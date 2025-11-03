import os, re, requests
from django.conf import settings
from django.db.models import Avg
from .models import KnowledgeBaseEntry, AIResponseRating


class AIService:
    def __init__(self):
        self.local_kb_path = settings.KNOWLEDGE_BASE_PATH
        
    def search_local_knowledge_base(self, query):
        """Search the local knowledge base text file first."""
        if not os.path.exists(self.local_kb_path):
            return None
        
        try:
            with open(self.local_kb_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            query_lower = query.lower()
            stop_words = {'what', 'is', 'the', 'a', 'an', 'how', 'do', 'does', 'can', 'i', 'you', 'we', 'are', 'to', 'for', 'of', 'with', 'on', 'at', 'by', 'from', 'as', 'about'}
            query_words = [w for w in query_lower.split() if w not in stop_words and len(w) > 2]
            
            if not query_words:
                query_words = query_lower.split()
            
            # Try to find paragraphs
            paragraphs = content.split('\n\n')
            best_matches = []
            
            for para in paragraphs:
                para_lower = para.lower()
                matches = sum(1 for word in query_words if word in para_lower)
                if matches > 0:
                    best_matches.append((matches, para.strip()))
            
            if best_matches:
                best_matches.sort(reverse=True, key=lambda x: x[0])
                top_match = best_matches[0]
                if top_match[0] >= len(query_words) * 0.5:
                    if len(best_matches) > 1 and best_matches[1][0] >= len(query_words) * 0.3:
                        return f"{top_match[1]}\n\n{best_matches[1][1]}"
                    return top_match[1]
            
            # Fallback: sentence search
            sentences = re.split(r'[.!?]\s+', content)
            sentence_matches = []
            
            for sentence in sentences:
                sentence_lower = sentence.lower()
                matches = sum(1 for word in query_words if word in sentence_lower)
                if matches > 0:
                    sentence_matches.append((matches, sentence.strip()))
            
            if sentence_matches:
                sentence_matches.sort(reverse=True, key=lambda x: x[0])
                if sentence_matches[0][0] >= 2:
                    result = '. '.join([s[1] for s in sentence_matches[:3]])
                    return result + '.' if not result.endswith('.') else result
                
        except Exception as e:
            print(f"Error reading knowledge base: {e}")
            return None
        
        return None
    
    def query_huggingface_api(self, query):
        """Query Hugging Face Inference API if local KB doesn't have answer."""
        if not settings.HUGGINGFACE_API_KEY:
            return "I couldn't find information about that in our knowledge base. For advanced AI responses, please configure a Hugging Face API key."
        
        try:
            headers = {
                "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"
            }
            
            prompt = f"Restaurant customer service question: {query}. Answer helpfully and concisely."
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_length": 200,
                    "temperature": 0.7
                }
            }
            
            response = requests.post(
                settings.HUGGINGFACE_API_URL,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], dict) and 'generated_text' in result[0]:
                        return result[0]['generated_text']
                    elif isinstance(result[0], str):
                        return result[0]
                elif isinstance(result, dict):
                    if 'generated_text' in result:
                        return result['generated_text']
                    elif 'answer' in result:
                        return result['answer']
                return str(result)
            else:
                return f"I'm sorry, I encountered an error. Please try again later."
                
        except Exception as e:
            return f"I'm sorry, I couldn't process your request. Please contact support."
    
    def get_ai_response(self, query, user=None):
        """Main method to get AI response"""
        from django.db import transaction
        
        source = 'local'
        answer = self.search_local_knowledge_base(query)
        
        if not answer:
            if settings.HUGGINGFACE_API_KEY:
                answer = self.query_huggingface_api(query)
                source = 'llm'
            else:
                answer = f"I couldn't find specific information about '{query}' in our knowledge base. The AI service (Hugging Face) is not configured. You can ask me about:\n\n- Our menu items and prices\n- How to place orders\n- Delivery information\n- VIP status and benefits\n- How to file complaints or compliments\n- Chef ratings"
                source = 'local'
        
        # Store the interaction
        kb_entry = None
        if source == 'local':
            kb_entry = KnowledgeBaseEntry.objects.filter(question=query).first()
            if not kb_entry:
                kb_entry = KnowledgeBaseEntry.objects.create(
                    question=query,
                    answer=answer,
                    rating=0.0,
                    rating_count=0
                )
        
        rating_record = AIResponseRating.objects.create(
            kb_entry=kb_entry,
            user=user,
            query=query,
            response=answer,
            rating=0,
            source=source
        )
        
        return {
            'answer': answer,
            'source': source,
            'rating_id': rating_record.id
        }
    
    def rate_ai_response(self, rating_id, rating_value):
        """Rate an AI response (0-5 stars)."""
        from django.db import transaction
        
        if rating_value < 0 or rating_value > 5:
            return False
        
        try:
            rating_record = AIResponseRating.objects.get(id=rating_id)
            rating_record.rating = rating_value
            rating_record.save()
            
            # If rating is 0 and there's a KB entry, flag it
            if rating_value == 0 and rating_record.kb_entry:
                kb_entry = rating_record.kb_entry
                kb_entry.flagged = True
                
                # Update average rating
                all_ratings = AIResponseRating.objects.filter(
                    kb_entry=kb_entry,
                    rating__gt=0
                )
                
                if all_ratings.exists():
                    kb_entry.rating = all_ratings.aggregate(avg=Avg('rating'))['avg'] or 0.0
                    kb_entry.rating_count = all_ratings.count()
                
                kb_entry.save()
            
            return True
        except AIResponseRating.DoesNotExist:
            return False


def get_ai_service():
    """Factory function to get AI service instance."""
    return AIService()

