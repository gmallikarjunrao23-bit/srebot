"""
AI Engine Integration
Connects to external AI API for intelligent analysis
"""
import aiohttp
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from config import settings


class AIEngine:
    """
    AI Operations Engine
    Integrates with external GPT API for intelligent infrastructure analysis
    """
    
    def __init__(self):
        self.api_url = settings.AI_API_URL
        self.timeout = settings.AI_API_TIMEOUT
    
    async def _call_api(self, query: str, prompt: str) -> Optional[str]:
        """Call the AI API with query and prompt"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "q": query,
                    "prompt": prompt
                }
                async with session.get(
                    self.api_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Handle different response formats
                        if isinstance(data, dict):
                            return data.get("response") or data.get("message") or data.get("result") or str(data)
                        elif isinstance(data, str):
                            return data
                        else:
                            return str(data)
                    else:
                        return f"AI API returned status {response.status}"
        except aiohttp.ClientError as e:
            return f"AI API connection error: {str(e)}"
        except Exception as e:
            return f"AI API error: {str(e)}"
    
    async def analyze_incident(
        self,
        monitor_name: str,
        monitor_type: str,
        error_message: str,
        status_code: Optional[int],
        response_time: float,
        previous_checks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        AI Incident Commander - Analyze an incident and provide insights
        """
        query = f"Incident on {monitor_name} ({monitor_type}): {error_message}"
        
        context = f"""
Monitor: {monitor_name}
Type: {monitor_type}
Error: {error_message}
Status Code: {status_code or 'N/A'}
Response Time: {response_time}ms
Recent History: {json.dumps(previous_checks[-5:]) if previous_checks else 'No recent data'}

Analyze this incident as an expert SRE. Provide:
1. Severity assessment (critical/high/medium/low)
2. Probable root cause
3. Business impact estimate
4. Recommended immediate actions
5. Estimated recovery time
6. Technical details for engineers
"""
        
        response = await self._call_api(query, context)
        
        return {
            "analysis": response,
            "severity_score": self._extract_severity(response),
            "recommendations": self._extract_recommendations(response),
            "impact_estimate": self._extract_impact(response),
            "recovery_estimate": self._extract_recovery_time(response),
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    async def generate_postmortem(
        self,
        incident: Dict[str, Any],
        check_results: List[Dict[str, Any]]
    ) -> str:
        """Generate incident postmortem report"""
        query = f"Generate postmortem for incident: {incident.get('title', 'Unknown')}"
        
        prompt = f"""
Incident Details:
{json.dumps(incident, indent=2, default=str)}

Check Results:
{json.dumps(check_results[-20:], indent=2, default=str)}

Generate a professional postmortem report including:
1. Executive Summary
2. Timeline of Events
3. Root Cause Analysis
4. Impact Assessment
5. Resolution Steps
6. Lessons Learned
7. Action Items
8. Prevention Measures
"""
        
        return await self._call_api(query, prompt) or "Postmortem generation failed"
    
    async def analyze_performance(
        self,
        monitor_name: str,
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze performance trends and provide recommendations"""
        query = f"Performance analysis for {monitor_name}"
        
        prompt = f"""
Performance Metrics:
{json.dumps(metrics, indent=2, default=str)}

Analyze as an SRE expert. Provide:
1. Health score (0-100)
2. Performance trend (improving/stable/degrading)
3. Key observations
4. Optimization recommendations
5. Risk assessment
"""
        
        response = await self._call_api(query, prompt)
        
        return {
            "analysis": response,
            "health_score": self._extract_health_score(response),
            "trend": self._extract_trend(response),
            "recommendations": self._extract_recommendations(response),
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    async def explain_for_executives(
        self,
        incident: Dict[str, Any]
    ) -> str:
        """Generate business-friendly explanation"""
        query = f"Explain incident to executives: {incident.get('title', '')}"
        
        prompt = f"""
Incident:
{json.dumps(incident, indent=2, default=str)}

Explain this incident in simple, business-friendly language suitable for executives and stakeholders. Include business impact and customer-facing implications.
"""
        
        return await self._call_api(query, prompt) or "Explanation generation failed"
    
    async def answer_question(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """AI Copilot - Answer natural language questions"""
        query = question
        
        prompt = f"""
You are an expert SRE AI Assistant. Answer the following question concisely and accurately.

Question: {question}

Context: {json.dumps(context, indent=2, default=str) if context else 'No additional context'}

Provide a clear, actionable response with specific technical details where relevant.
"""
        
        return await self._call_api(query, prompt) or "Unable to process question"
    
    # Helper methods to extract structured data from AI responses
    def _extract_severity(self, text: str) -> float:
        """Extract severity score from AI response"""
        text_lower = text.lower()
        if "critical" in text_lower:
            return 0.95
        elif "high" in text_lower:
            return 0.75
        elif "medium" in text_lower:
            return 0.5
        elif "low" in text_lower:
            return 0.25
        return 0.5
    
    def _extract_health_score(self, text: str) -> float:
        """Extract health score from AI response"""
        import re
        match = re.search(r'(\d+)', text)
        if match:
            score = int(match.group(1))
            if 0 <= score <= 100:
                return float(score)
        return 85.0
    
    def _extract_trend(self, text: str) -> str:
        """Extract trend from AI response"""
        text_lower = text.lower()
        if "improving" in text_lower or "better" in text_lower:
            return "improving"
        elif "degrading" in text_lower or "worsening" in text_lower or "declining" in text_lower:
            return "degrading"
        return "stable"
    
    def _extract_recommendations(self, text: str) -> List[str]:
        """Extract recommendations from AI response"""
        lines = text.split("\n")
        recommendations = []
        in_recommendations = False
        
        for line in lines:
            line = line.strip()
            if "recommend" in line.lower() or "action" in line.lower() or "step" in line.lower():
                in_recommendations = True
            if in_recommendations and line and (line.startswith("-") or line.startswith("*") or line[0].isdigit()):
                recommendations.append(line.lstrip("-*0123456789. ").strip())
        
        return recommendations[:5] if recommendations else ["Monitor closely and review configuration"]
    
    def _extract_impact(self, text: str) -> str:
        """Extract impact estimate from AI response"""
        lines = text.split("\n")
        for line in lines:
            if "impact" in line.lower():
                return line.split(":", 1)[-1].strip() if ":" in line else line.strip()
        return "Impact assessment unavailable"
    
    def _extract_recovery_time(self, text: str) -> str:
        """Extract recovery time estimate from AI response"""
        lines = text.split("\n")
        for line in lines:
            if "recovery" in line.lower() or "time" in line.lower():
                return line.split(":", 1)[-1].strip() if ":" in line else line.strip()
        return "Unknown"


# Global AI Engine instance
ai_engine = AIEngine()

