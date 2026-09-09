"""
Knowledge Service — Question Answering
=======================================
Answers general knowledge questions using the Wikipedia API.
"""

import wikipedia


def answer_question(topic: str) -> dict:
    """
    Answer a general knowledge question by searching Wikipedia.
    
    Args:
        topic: The topic or question to look up
        
    Returns:
        dict with keys:
            - success (bool)
            - answer (str): The answer text
            - title (str): Wikipedia article title
            - url (str): Wikipedia article URL
    """
    if not topic or len(topic.strip()) < 2:
        return {
            "success": False,
            "answer": "Could you please be more specific about what you'd like to know?",
            "title": "",
            "url": ""
        }

    try:
        # Try to get a summary directly
        summary = wikipedia.summary(topic, sentences=3, auto_suggest=True)
        page = wikipedia.page(topic, auto_suggest=True)

        return {
            "success": True,
            "answer": summary,
            "title": page.title,
            "url": page.url
        }

    except wikipedia.DisambiguationError as e:
        # Multiple possible articles — pick the first option
        try:
            first_option = e.options[0]
            summary = wikipedia.summary(first_option, sentences=3)
            page = wikipedia.page(first_option)
            return {
                "success": True,
                "answer": f"Here's what I found about '{first_option}': {summary}",
                "title": page.title,
                "url": page.url
            }
        except Exception:
            options_text = ", ".join(e.options[:5])
            return {
                "success": False,
                "answer": f"'{topic}' could refer to several things: {options_text}. Could you be more specific?",
                "title": "",
                "url": ""
            }

    except wikipedia.PageError:
        # No article found — try searching
        try:
            search_results = wikipedia.search(topic, results=3)
            if search_results:
                first_result = search_results[0]
                summary = wikipedia.summary(first_result, sentences=3)
                page = wikipedia.page(first_result)
                return {
                    "success": True,
                    "answer": f"I found information about '{first_result}': {summary}",
                    "title": page.title,
                    "url": page.url
                }
            else:
                return {
                    "success": False,
                    "answer": f"I couldn't find any information about '{topic}'. Try rephrasing your question.",
                    "title": "",
                    "url": ""
                }
        except Exception:
            return {
                "success": False,
                "answer": f"I couldn't find reliable information about '{topic}'.",
                "title": "",
                "url": ""
            }

    except Exception as e:
        return {
            "success": False,
            "answer": f"I had trouble looking that up. Error: {str(e)}",
            "title": "",
            "url": ""
        }
