import base64
_o=chr(91); _c=chr(93)
s1 = '        print(''cents?'', m.group(0)'+_o+':80'+_c+', v, ''eur'', v/100)\n'
s2 = '        print(''eur?'', m.group(0)'+_o+':80'+_c+', v)\n'
print(base64.b64encode(s1.encode()).decode())
print(base64.b64encode(s2.encode()).decode())
