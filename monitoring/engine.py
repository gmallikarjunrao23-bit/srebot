"""
Monitoring Engine
Asynchronous HTTP/TCP/PING checking with retries and intelligent validation
"""
import asyncio
import aiohttp
import aiohttp.client_exceptions
import dns.resolver
import ssl
import socket
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from domain import Monitor, MonitorType, CheckResult, MonitorStatus
from config import settings


class MonitoringEngine:
    """
    Enterprise Monitoring Engine
    Handles all types of infrastructure checks with intelligent validation
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._ssl_context = ssl.create_default_context()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=settings.MONITOR_TIMEOUT)
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
                enable_cleanup_closed=True,
                force_close=True,
            )
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                raise_for_status=False
            )
        return self.session
    
    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def check(self, monitor: Monitor) -> CheckResult:
        """
        Perform a check based on monitor type
        Returns CheckResult with full diagnostics
        """
        check_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        
        result = CheckResult(
            id=check_id,
            monitor_id=monitor.id,
            started_at=started_at,
            region=monitor.region
        )
        
        try:
            if monitor.monitor_type in [MonitorType.HTTP, MonitorType.HTTPS, MonitorType.API]:
                await self._check_http(monitor, result)
            elif monitor.monitor_type == MonitorType.TCP:
                await self._check_tcp(monitor, result)
            elif monitor.monitor_type == MonitorType.PING:
                await self._check_ping(monitor, result)
            elif monitor.monitor_type == MonitorType.DNS:
                await self._check_dns(monitor, result)
            elif monitor.monitor_type == MonitorType.SSL:
                await self._check_ssl(monitor, result)
            elif monitor.monitor_type == MonitorType.KEYWORD:
                await self._check_keyword(monitor, result)
            else:
                result.error_message = f"Unsupported monitor type: {monitor.monitor_type}"
                result.error_type = "unsupported_type"
        except Exception as e:
            result.error_message = str(e)
            result.error_type = type(e).__name__
        
        result.completed_at = datetime.utcnow()
        if result.started_at and result.completed_at:
            delta = result.completed_at - result.started_at
            result.response_time_ms = round(delta.total_seconds() * 1000, 2)
        
        return result
    
    async def _check_http(self, monitor: Monitor, result: CheckResult):
        """HTTP/HTTPS/API check with full validation"""
        session = await self._get_session()
        
        headers = {
            "User-Agent": "SRE-Bot-Monitor/1.0 (Enterprise Monitoring Platform)",
            "Accept": "*/*",
            **monitor.custom_headers
        }
        
        try:
            async with session.get(
                monitor.url,
                headers=headers,
                ssl=self._ssl_context if monitor.url.startswith("https") else False,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=monitor.timeout)
            ) as response:
                result.status_code = response.status
                result.response_headers = dict(response.headers)
                
                # Check status code
                if response.status in monitor.expected_status_codes:
                    result.is_up = True
                else:
                    result.is_up = False
                    result.error_message = f"Unexpected status code: {response.status}"
                    result.error_type = "status_code_mismatch"
                
                # Check keyword if specified
                if monitor.expected_keyword and result.is_up:
                    try:
                        text = await response.text()
                        result.response_body = text[:5000]  # Limit storage
                        if monitor.expected_keyword not in text:
                            result.is_up = False
                            result.error_message = f"Keyword '{monitor.expected_keyword}' not found"
                            result.error_type = "keyword_missing"
                    except Exception as e:
                        result.is_up = False
                        result.error_message = f"Failed to read response body: {str(e)}"
                        result.error_type = "body_read_error"
                
                # Check SSL info for HTTPS
                if monitor.url.startswith("https"):
                    result.ssl_valid = True
                    # Extract SSL expiry if possible
                    try:
                        hostname = monitor.url.split("://")[-1].split("/")[0].split(":")[0]
                        context = ssl.create_default_context()
                        with socket.create_connection((hostname, 443), timeout=5) as sock:
                            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                                cert = ssock.getpeercert()
                                if cert and "notAfter" in cert:
                                    from datetime import strptime
                                    expiry = strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                                    result.ssl_expiry_date = expiry
                    except Exception:
                        pass
        
        except aiohttp.ClientResponseError as e:
            result.status_code = e.status
            result.is_up = False
            result.error_message = f"HTTP Error: {e.status} - {e.message}"
            result.error_type = "http_error"
        
        except aiohttp.ClientConnectorError as e:
            result.is_up = False
            result.error_message = f"Connection failed: {str(e)}"
            result.error_type = "connection_error"
        
        except asyncio.TimeoutError:
            result.is_up = False
            result.error_message = f"Request timed out after {monitor.timeout}s"
            result.error_type = "timeout"
        
        except aiohttp.ClientError as e:
            result.is_up = False
            result.error_message = f"Client error: {str(e)}"
            result.error_type = "client_error"
    
    async def _check_tcp(self, monitor: Monitor, result: CheckResult):
        """TCP port check"""
        try:
            # Parse host:port from URL
            parts = monitor.url.replace("tcp://", "").split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 80
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=monitor.timeout
            )
            writer.close()
            await writer.wait_closed()
            result.is_up = True
        
        except asyncio.TimeoutError:
            result.is_up = False
            result.error_message = "TCP connection timed out"
            result.error_type = "tcp_timeout"
        
        except Exception as e:
            result.is_up = False
            result.error_message = f"TCP connection failed: {str(e)}"
            result.error_type = "tcp_error"
    
    async def _check_ping(self, monitor: Monitor, result: CheckResult):
        """ICMP ping check (using system ping command)"""
        import subprocess
        
        host = monitor.url.replace("ping://", "").replace("http://", "").replace("https://", "").split("/")[0]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", "1", "-W", str(monitor.timeout), host,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=monitor.timeout + 2
            )
            
            if proc.returncode == 0:
                result.is_up = True
                # Extract response time from ping output
                output = stdout.decode()
                import re
                time_match = re.search(r'time=([\d.]+)', output)
                if time_match:
                    result.response_time_ms = float(time_match.group(1))
            else:
                result.is_up = False
                result.error_message = f"Host unreachable: {host}"
                result.error_type = "ping_failed"
        
        except asyncio.TimeoutError:
            result.is_up = False
            result.error_message = "Ping timed out"
            result.error_type = "ping_timeout"
        
        except Exception as e:
            result.is_up = False
            result.error_message = f"Ping failed: {str(e)}"
            result.error_type = "ping_error"
    
    async def _check_dns(self, monitor: Monitor, result: CheckResult):
        """DNS resolution check"""
        hostname = monitor.url.replace("dns://", "").replace("http://", "").replace("https://", "").split("/")[0]
        
        try:
            start = datetime.utcnow()
            answers = dns.resolver.resolve(hostname, "A")
            end = datetime.utcnow()
            
            result.is_up = True
            result.dns_resolution_time = round((end - start).total_seconds() * 1000, 2)
            result.response_body = f"Resolved to: {', '.join([str(r) for r in answers])}"
        
        except dns.resolver.NXDOMAIN:
            result.is_up = False
            result.error_message = f"Domain does not exist: {hostname}"
            result.error_type = "dns_nxdomain"
        
        except dns.resolver.Timeout:
            result.is_up = False
            result.error_message = "DNS resolution timed out"
            result.error_type = "dns_timeout"
        
        except Exception as e:
            result.is_up = False
            result.error_message = f"DNS resolution failed: {str(e)}"
            result.error_type = "dns_error"
    
    async def _check_ssl(self, monitor: Monitor, result: CheckResult):
        """SSL certificate check"""
        hostname = monitor.url.replace("ssl://", "").replace("https://", "").split("/")[0].split(":")[0]
        
        try:
            context = ssl.create_default_context()
            start = datetime.utcnow()
            
            with socket.create_connection((hostname, 443), timeout=monitor.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    end = datetime.utcnow()
                    
                    result.is_up = True
                    result.ssl_valid = True
                    result.response_time_ms = round((end - start).total_seconds() * 1000, 2)
                    
                    if cert and "notAfter" in cert:
                        from datetime import strptime
                        expiry = strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                        result.ssl_expiry_date = expiry
                        
                        # Check if expiring soon
                        days_until_expiry = (expiry - datetime.utcnow()).days
                        if days_until_expiry < 7:
                            result.is_up = False
                            result.error_message = f"SSL expires in {days_until_expiry} days!"
                            result.error_type = "ssl_expiring_soon"
        
        except ssl.SSLError as e:
            result.is_up = False
            result.error_message = f"SSL error: {str(e)}"
            result.error_type = "ssl_error"
        
        except Exception as e:
            result.is_up = False
            result.error_message = f"SSL check failed: {str(e)}"
            result.error_type = "ssl_check_error"
    
    async def _check_keyword(self, monitor: Monitor, result: CheckResult):
        """Keyword presence check (uses HTTP check with keyword validation)"""
        await self._check_http(monitor, result)
    
    async def check_with_retries(self, monitor: Monitor) -> CheckResult:
        """Check with intelligent retry logic"""
        last_result = None
        
        for attempt in range(monitor.retries + 1):
            result = await self.check(monitor)
            last_result = result
            
            if result.is_up:
                return result
            
            if attempt < monitor.retries:
                await asyncio.sleep(monitor.retry_delay)
        
        return last_result


# Global monitoring engine instance
monitoring_engine = MonitoringEngine()

