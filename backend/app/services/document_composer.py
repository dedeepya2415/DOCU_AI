import re
from datetime import datetime

class DocumentComposer:
    """
    Transforms raw extracted strings into polished legal text based on semantic field types.
    """
    def format_fields(self, schema: dict, field_values: dict) -> dict:
        """For blank templates"""
        formatted = {}
        for idx_str, raw_value in field_values.items():
            if not raw_value:
                formatted[idx_str] = raw_value
                continue
                
            info = schema.get(idx_str, {})
            field_type = info.get("field_type", "")
            
            formatted[idx_str] = self._format_value(field_type, str(raw_value))
            
        return formatted

    def format_prefilled(self, schema: list, mappings: list) -> list:
        """For pre-filled templates"""
        # Build lookup from search_text -> field_type
        type_lookup = {item["search_text"]: item.get("field_type", "") for item in schema}
        
        formatted_mappings = []
        for m in mappings:
            search = m["search"]
            raw_replace = m["replace"]
            field_type = type_lookup.get(search, "")
            
            formatted_mappings.append({
                "search": search,
                "replace": self._format_value(field_type, raw_replace)
            })
        return formatted_mappings

    def format_native_context(self, context: dict) -> dict:
        """For natively tagged Jinja2 templates (Mode 3)"""
        formatted = {}
        for key, value in context.items():
            if not value:
                formatted[key] = value
                continue
                
            k_low = key.lower()
            # Infer basic type from variable name suffix/keywords
            if "price" in k_low or "amount" in k_low or "cost" in k_low:
                formatted[key] = self._format_currency(str(value))
            elif "date" in k_low:
                formatted[key] = self._format_date(str(value))
            elif "name" in k_low:
                formatted[key] = str(value).title()
            else:
                formatted[key] = str(value)
                
        return formatted

    def _format_value(self, field_type: str, value: str) -> str:
        if not value:
            return value
            
        value = value.strip()
        
        if field_type == "sale_price":
            return self._format_currency(value)
        elif field_type == "name":
            return value.title()
        elif field_type in ("date_day", "registration_date"):
            return self._format_date(value)
        
        return value

    def _format_currency(self, value: str) -> str:
        # Extract numbers only
        nums = re.sub(r'[^\d]', '', value)
        if not nums:
            return value
            
        try:
            num = int(nums)
        except ValueError:
            return value
            
        words = self._num_to_indian_words(num)
        formatted_num = self._in_commas(num)
        
        return f"Rs. {formatted_num}/- (Rupees {words.title()} Only)"

    def _in_commas(self, number: int) -> str:
        s = str(number)
        if len(s) <= 3:
            return s
        last3 = s[-3:]
        rest = s[:-3]
        rest_chunks = []
        while len(rest) > 0:
            rest_chunks.append(rest[-2:])
            rest = rest[:-2]
        rest_chunks.reverse()
        return ",".join(rest_chunks) + "," + last3

    def _num_to_indian_words(self, num: int) -> str:
        if num == 0:
            return "Zero"
            
        ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
                "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
        
        def _convert_below_100(n):
            if n < 20: return ones[n]
            return tens[n // 10] + (" " + ones[n % 10] if (n % 10 != 0) else "")
            
        def _convert_below_1000(n):
            if n < 100: return _convert_below_100(n)
            return ones[n // 100] + " Hundred" + ((" and " + _convert_below_100(n % 100)) if (n % 100 != 0) else "")
            
        res = ""
        
        if num >= 10000000:
            crores = num // 10000000
            res += _convert_below_100(crores) + " Crore "
            num %= 10000000
            
        if num >= 100000:
            lakhs = num // 100000
            res += _convert_below_100(lakhs) + " Lakh "
            num %= 100000
            
        if num >= 1000:
            thousands = num // 1000
            res += _convert_below_100(thousands) + " Thousand "
            num %= 1000
            
        if num > 0:
            res += _convert_below_1000(num)
            
        return res.strip()

    def _format_date(self, date_str: str) -> str:
        # Expected format YYYY-MM-DD
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            
            day = dt.day
            suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
            
            return dt.strftime(f"{day}{suffix} %B, %Y")
        except ValueError:
            return date_str
