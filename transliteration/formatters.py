"""
Transliteration output formatters for clean, readable text.
"""

import re
from typing import Dict, Any

class TransliterationFormatter:
    """
    Formats transliteration output to be more readable and user-friendly.
    """
    
    def __init__(self):
        # Character mappings for cleaning up transliteration
        self.character_replacements = {
            # Non-standard characters to standard ones
            'ò': 'o',
            'ḻ': 'l', 
            'ṅ': 'ng',
            'ṇ': 'n',
            'ṭ': 't',
            'ḍ': 'd',
            'ṣ': 'sh',
            'ṃ': 'm',
            'ḥ': 'h',
            'ṁ': 'm',
            
            # Telugu specific
            'ḷ': 'l',
            'ṛ': 'r',
            'ṝ': 'r',
            
            # Clean up mixed case issues
            'I': 'i',
            'A': 'a',
            'U': 'u',
            'E': 'e',
            'O': 'o',
        }
        
        # Vowel length mappings for user-friendly format
        self.vowel_length_mappings = {
            'ī': 'ee',
            'ā': 'aa', 
            'ū': 'uu',
            'ē': 'ee',
            'ō': 'oo',
            'ṛ': 'ri',
            'ṝ': 'ri',
        }
        
        # Common word corrections for better readability
        self.word_corrections = {
            'dIpòvaLi': 'Deepavali',
            'dīpòvaḻi': 'Deepavali',
            'dIpAvalI': 'Deepavali',
            'dīpāvalī': 'Deepavali',
            'dIpAvaLi': 'Deepavali',
            'dīpāvaḻi': 'Deepavali',
            'avItAlat': 'Aveetalat',
            'avītālat': 'Aveetalat',
            'dipavaLi': 'Deepavali',  # Handle partial corrections
        }
        
        # English to Indian script common corrections
        self.english_to_indian_corrections = {
            'Changes': 'चेंजेस',
            'Bhatta': 'भट्टा',
            'Fall': 'फॉल',
            'Hello': 'हेलो',
            'India': 'इंडिया',
            'Welcome': 'वेलकम',
        }

    def clean_transliteration(self, text: str, target_script: str) -> str:
        """
        Clean and format transliteration output based on target script.
        
        Args:
            text: Raw transliteration output
            target_script: Target script code (e.g., sanscript.ITRANS)
            
        Returns:
            Cleaned and formatted text
        """
        if not text:
            return text
        
        # Check if text is in Indian script (should not apply English formatting)
        is_indian_script = any('\u0900' <= char <= '\u097f' for char in text) or \
                          any('\u0c00' <= char <= '\u0c7f' for char in text) or \
                          any('\u0b80' <= char <= '\u0bff' for char in text) or \
                          any('\u0c80' <= char <= '\u0cff' for char in text) or \
                          any('\u0a80' <= char <= '\u0aff' for char in text)
        
        # If text is in Indian script, clean it differently
        if is_indian_script:
            cleaned_text = self._clean_indian_script(text)
        else:
            # Apply word corrections first
            cleaned_text = text
            for incorrect, correct in self.word_corrections.items():
                if incorrect.lower() in cleaned_text.lower():
                    cleaned_text = cleaned_text.replace(incorrect, correct)
            
            # Apply English to Indian script corrections if target is Indian script
            # Check if we have mixed English/Indian script text that needs correction
            has_english_caps = any(c.isupper() and c.isalpha() for c in cleaned_text)
            has_indian_script = any('\u0900' <= char <= '\u097f' for char in cleaned_text) or \
                               any('\u0c00' <= char <= '\u0c7f' for char in cleaned_text) or \
                               any('\u0b80' <= char <= '\u0bff' for char in cleaned_text)
            
            if has_english_caps and has_indian_script:
                # Apply corrections for common English words in mixed text
                for english_word, indian_word in self.english_to_indian_corrections.items():
                    if english_word in cleaned_text:
                        cleaned_text = cleaned_text.replace(english_word, indian_word)
            
            # Clean up characters
            for old_char, new_char in self.character_replacements.items():
                cleaned_text = cleaned_text.replace(old_char, new_char)
            
            # For Roman/English output, apply additional formatting
            if target_script in ['roman', 'english', 'ITRANS', 'Latin'] or str(target_script) in ['ITRANS', 'Latin']:
                cleaned_text = self._format_for_english(cleaned_text)
        
        # Clean up extra spaces and normalize
        cleaned_text = ' '.join(cleaned_text.split())
        
        return cleaned_text

    def _clean_indian_script(self, text: str) -> str:
        """
        Clean text that's already in Indian script (remove mixed capitalization).
        """
        import re
        
        # Define Unicode ranges for Indian scripts
        devanagari_range = r'[\u0900-\u097f]'
        telugu_range = r'[\u0c00-\u0c7f]'
        tamil_range = r'[\u0b80-\u0bff]'
        kannada_range = r'[\u0c80-\u0cff]'
        malayalam_range = r'[\u0d00-\u0d7f]'
        gujarati_range = r'[\u0a80-\u0aff]'
        bengali_range = r'[\u0980-\u09ff]'
        punjabi_range = r'[\u0a00-\u0a7f]'
        
        # Combined Indian script pattern
        indian_scripts = f"({devanagari_range}|{telugu_range}|{tamil_range}|{kannada_range}|{malayalam_range}|{gujarati_range}|{bengali_range}|{punjabi_range})"
        
        # Replace English capital letters before Indian script characters
        cleaned = re.sub(f'([A-Z])({indian_scripts})', lambda m: m.group(1).lower() + m.group(2), text)
        
        # Replace English capital letters after Indian script characters  
        cleaned = re.sub(f'({indian_scripts})([A-Z])', lambda m: m.group(1) + m.group(2).lower(), cleaned)
        
        # Replace English capital letters between Indian script characters
        cleaned = re.sub(f'({indian_scripts})([A-Z])({indian_scripts})', lambda m: m.group(1) + m.group(2).lower() + m.group(3), cleaned)
        
        # Remove standalone English capital letters
        cleaned = re.sub(r'\b[A-Z]\b', lambda m: m.group(0).lower(), cleaned)
        
        return cleaned

    def _format_for_english(self, text: str) -> str:
        """
        Format text specifically for English/Roman output.
        """
        # Apply vowel length mappings for user-friendly format
        for diacritic, replacement in self.vowel_length_mappings.items():
            text = text.replace(diacritic, replacement)
        
        # Convert to title case for proper nouns (words that look like names/places)
        words = text.split()
        formatted_words = []
        
        for word in words:
            # Skip if already properly formatted (contains uppercase)
            if word.isupper() or (word[0].isupper() and word[1:].islower()):
                formatted_words.append(word)
                continue
                
            # If word contains long vowels or looks like a proper noun, use title case
            if (any(char in word for char in ['aa', 'ee', 'ii', 'oo', 'uu']) or 
                len(word) > 4 or 
                word.islower()):
                formatted_words.append(word.title())
            else:
                formatted_words.append(word)
        
        return ' '.join(formatted_words)

    def format_transliterations(self, transliterations: Dict[str, str]) -> Dict[str, str]:
        """
        Format all transliteration outputs in a dictionary.
        
        Args:
            transliterations: Dictionary with script names as keys and transliterated text as values
            
        Returns:
            Dictionary with formatted transliterations
        """
        formatted_transliterations = {}
        
        for script_name, text in transliterations.items():
            # Determine target script type
            if any(keyword in script_name.lower() for keyword in ['roman', 'english', 'itrans', 'latin']):
                target_script = 'roman'
            elif 'iast' in script_name.lower():
                target_script = 'iast'
            else:
                target_script = 'other'
            
            formatted_transliterations[script_name] = self.clean_transliteration(text, target_script)
        
        return formatted_transliterations

    def add_pronunciation_guide(self, text: str, target_script: str) -> Dict[str, str]:
        """
        Add pronunciation guide for complex transliterations.
        
        Args:
            text: Transliterated text
            target_script: Target script
            
        Returns:
            Dictionary with text and pronunciation guide
        """
        result = {'text': text}
        
        if target_script in ['roman', 'english']:
            # Create simple pronunciation guide
            pronunciation = text.lower()
            
            # Replace long vowels with phonetic equivalents
            pronunciation = pronunciation.replace('aa', 'aa (as in car)')
            pronunciation = pronunciation.replace('ee', 'ee (as in see)')
            pronunciation = pronunciation.replace('ii', 'ii (as in ski)')
            pronunciation = pronunciation.replace('oo', 'oo (as in too)')
            pronunciation = pronunciation.replace('uu', 'uu (as in blue)')
            
            # Add syllable breaks for long words
            if len(text.split()) == 1 and len(text) > 6:
                # Simple syllable breaking (basic heuristic)
                syllables = self._break_into_syllables(text)
                result['pronunciation'] = f"{text} → {syllables}"
            
        return result

    def _break_into_syllables(self, word: str) -> str:
        """
        Basic syllable breaking for pronunciation guide.
        """
        # Simple heuristic: break at vowel-consonant boundaries
        syllables = []
        current_syllable = ""
        
        for i, char in enumerate(word):
            current_syllable += char
            
            # Break after vowel if next char is consonant and not end of word
            if (i < len(word) - 1 and 
                char.lower() in 'aeiou' and 
                word[i + 1].lower() not in 'aeiou'):
                syllables.append(current_syllable)
                current_syllable = ""
        
        if current_syllable:
            syllables.append(current_syllable)
        
        return '-'.join(syllables)


# Global formatter instance
formatter = TransliterationFormatter()
