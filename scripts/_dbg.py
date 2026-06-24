import re
_o=chr(91); _c=chr(93); q=chr(34)
pat = q+'(?:'+_o+'^'+q+'*(?:price|Price|rabatt|Rabatt|discount|Discount)'+_o+'^'+q+'*)'+q+r'\s*:\s*('+_o+'0-9.'+_c+'+)'
print(repr(pat))
m=re.search(pat, '" listPrice\: 1529')
print(m)
print(m.groups() if m else None)
