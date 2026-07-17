import fitz

class LayoutEngine:
    """
    Given a bounding box and target text, the LayoutEngine intelligently wraps
    text or dynamically scales font size to ensure a perfect legal document layout.
    """
    def __init__(self, fontname="helv", default_fontsize=12, min_fontsize=8):
        self.fontname = fontname
        self.default_fontsize = default_fontsize
        self.min_fontsize = min_fontsize
        
    def fit_text_to_box(self, text: str, bbox: tuple) -> tuple:
        """
        Calculates how to fit text gracefully into a bounding box (x0, y0, x1, y1).
        
        Returns:
            (final_fontsize, [(line_str, float_x, float_y_baseline), ...])
        """
        x0, y0, x1, y1 = bbox
        box_width = x1 - x0
        box_height = y1 - y0
        
        # If no width, just dump it
        if box_width <= 0:
            return self.default_fontsize, [(text, x0, y1)]
            
        # Try progressively smaller font sizes to fit it properly
        start_size = int(self.default_fontsize)
        min_size = int(self.min_fontsize)
        for fontsize in range(start_size, min_size - 1, -1):
            
            # Simple case: fits on a single line perfectly
            width = fitz.get_text_length(text, fontname=self.fontname, fontsize=fontsize)
            if width <= box_width:
                y_baseline = y1 - (fontsize * 0.2) 
                return fontsize, [(text, x0, y_baseline)]
                
            # For multi-line, bounding boxes for underscores usually aren't very tall
            # But just in case it is a multiline blank (e.g. Schedule box):
            line_height = fontsize * 1.2
            max_lines = max(1, int(box_height // line_height))
            
            if max_lines > 1:
                # Try word wrapping
                words = text.split()
                lines = []
                current_line = ""
                
                success = True
                for word in words:
                    test_str = current_line + " " + word if current_line else word
                    test_w = fitz.get_text_length(test_str, fontname=self.fontname, fontsize=fontsize)
                    if test_w > box_width:
                        if not current_line:
                            success = False # A single word cannot fit
                            break
                        lines.append(current_line)
                        current_line = word
                    else:
                        current_line = test_str
                
                if success:
                    if current_line:
                        lines.append(current_line)
                        
                    # If it successfully wrapped, ensure we don't draw overlapping the next paragraph
                    if len(lines) <= max_lines:
                        rendered_lines = []
                        start_y = y0 + (fontsize * 0.9)  # Proper baseline calculation
                        for i, l in enumerate(lines):
                            y_pos = start_y + (i * line_height)
                            rendered_lines.append((l, x0, y_pos))
                        return fontsize, rendered_lines
                    
        # Fallback: Just squeeze it in at the min font size on ONE line. No wrapping.
        y_baseline = y1 - (self.min_fontsize * 0.2)
        # Squeeze horizontal width by returning a single line
        return self.min_fontsize, [(text, x0, y_baseline)]
