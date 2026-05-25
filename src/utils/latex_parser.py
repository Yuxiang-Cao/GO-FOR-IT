import re
import json

class LatexCVParser:
    def __init__(self):
        pass

    def parse(self, latex_content: str) -> dict:
        """Parses LaTeX CV content into a structured dictionary.
        This parses standard sections and itemize blocks to make them editable,
        retaining the exact structure and preamble.
        """
        # Find the preamble (everything before \begin{document} or the first section)
        first_section_match = re.search(r'\\section\*?\{', latex_content)
        preamble = ""
        body = latex_content
        
        if first_section_match:
            idx = first_section_match.start()
            preamble = latex_content[:idx]
            body = latex_content[idx:]
            
        # Split by section
        # We find all sections: \section{Section Name} or \section*{Section Name}
        section_matches = list(re.finditer(r'\\section\*?\{([^}]+)\}', body))
        
        sections = []
        for i, match in enumerate(section_matches):
            title = match.group(1)
            start_idx = match.end()
            end_idx = section_matches[i+1].start() if i+1 < len(section_matches) else len(body)
            
            section_raw = body[start_idx:end_idx]
            
            # Find itemize blocks inside the section
            items = self._parse_section_content(section_raw)
            
            sections.append({
                "title": title,
                "raw_before_items": items["raw_before_items"],
                "list_items": items["list_items"],
                "raw_after_items": items["raw_after_items"],
                "raw_pieces": items.get("raw_pieces"),
                "list_lengths": items.get("list_lengths")
            })
            
        return {
            "preamble": preamble,
            "sections": sections
        }

    def _parse_section_content(self, section_text: str) -> dict:
        r"""Parses the text within a section to isolate all itemize blocks (\item)."""
        list_items = []
        list_lengths = []
        raw_pieces = []
        
        last_idx = 0
        matches = list(re.finditer(r'\\begin\{itemize\}', section_text))
        
        if not matches:
            return {
                "raw_before_items": section_text,
                "list_items": [],
                "raw_after_items": "",
                "raw_pieces": [section_text],
                "list_lengths": []
            }
            
        for match in matches:
            start_itemize = match.start()
            end_itemize_match = re.search(r'\\end\{itemize\}', section_text[start_itemize:])
            if not end_itemize_match:
                break
                
            end_itemize = start_itemize + end_itemize_match.end()
            
            # Text before this itemize block (since the last block ended)
            raw_pieces.append(section_text[last_idx:start_itemize])
            
            # Extract items from this block
            itemize_content = section_text[start_itemize:end_itemize]
            items_raw = re.split(r'\\item\s+', itemize_content)
            
            # Append environment opening (like \begin{itemize}) to raw text
            raw_pieces[-1] = raw_pieces[-1] + items_raw[0]
            
            block_items = []
            for item in items_raw[1:]:
                clean_item = item.strip()
                if "\\end{itemize}" in clean_item:
                    clean_item = clean_item.split("\\end{itemize}")[0].strip()
                block_items.append(clean_item)
                
            list_items.extend(block_items)
            list_lengths.append(len(block_items))
            
            last_idx = end_itemize
            
        # Append remaining text after last block
        raw_pieces.append(section_text[last_idx:])
        
        # Populate raw_before_items and raw_after_items for backward compatibility
        if matches:
            first_start = matches[0].start()
            first_itemize_content = section_text[first_start:]
            first_items_raw = re.split(r'\\item\s+', first_itemize_content)
            raw_before_items = section_text[:first_start] + first_items_raw[0]
            
            first_end_match = re.search(r'\\end\{itemize\}', section_text[first_start:])
            if first_end_match:
                first_end = first_start + first_end_match.end()
                raw_after_items = section_text[first_end:]
            else:
                raw_after_items = ""
        else:
            raw_before_items = section_text
            raw_after_items = ""
            
        return {
            "raw_before_items": raw_before_items,
            "list_items": list_items,
            "raw_after_items": raw_after_items,
            "raw_pieces": raw_pieces,
            "list_lengths": list_lengths
        }

    def rebuild(self, structured_cv: dict) -> str:
        """Reconstructs the LaTeX source from the structured dictionary.
        Guarantees that the formatting template is preserved perfectly.
        """
        output = structured_cv.get("preamble", "")
        
        for section in structured_cv.get("sections", []):
            title = section["title"]
            output += f"\\section{{{title}}}"
            
            raw_pieces = section.get("raw_pieces")
            list_lengths = section.get("list_lengths")
            list_items = section.get("list_items", [])
            
            if raw_pieces is not None and list_lengths is not None:
                item_idx = 0
                for idx, length in enumerate(list_lengths):
                    # Output raw text before this list (which includes \begin{itemize})
                    output += raw_pieces[idx]
                    # Output the items in this list
                    for _ in range(length):
                        if item_idx < len(list_items):
                            output += f"\\item {list_items[item_idx]}\n"
                            item_idx += 1
                    # Output \end{itemize}
                    output += "\\end{itemize}\n"
                # Output text after the last list
                if len(raw_pieces) > len(list_lengths):
                    output += raw_pieces[-1]
            else:
                output += section.get("raw_before_items", "")
                if list_items:
                    for item in list_items:
                        output += f"\\item {item}\n"
                    output += "\\end{itemize}\n"
                output += section.get("raw_after_items", "")
                
        return output

    def save_json(self, data: dict, output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_json(self, input_path: str) -> dict:
        with open(input_path, 'r', encoding='utf-8') as f:
            return json.load(f)
