import Sword as SW
from .debug import dprint, WARNING

def to_unicode(text, mod=None):
	if mod is None:
		#dprint(WARNING, "mod is None in to_unicode")
		#get_traceback()
		encoding = "utf8"
	else:
		encoding = "cp1252"
	
		if ord(mod.Encoding()) == SW.ENC_UTF8:
			encoding = "utf8"
	
	return text.decode(encoding, "replace")

def to_str(text, mod=None):
	if mod is None:
		encoding = "utf8"
	else:
		encoding = "cp1252"
	
		if ord(mod.Encoding()) == SW.ENC_UTF8:
			encoding = "utf8"

	
	return text.encode(encoding, "replace")

def utf8_to_unicode(text):
	return text.decode("utf8", "replace")
	
def cp1252_to_unicode(text):
	return text.decode("cp1252", "replace")
	
lookup = dict(utf8=utf8_to_unicode, cp1252=cp1252_to_unicode)

def get_to_unicode(mod):
	return lookup[get_module_encoding(mod)]
	
	
def get_module_encoding(module):
	encoding = "cp1252"
	
	if ord(module.Encoding()) == SW.ENC_UTF8:
		encoding = "utf8"

	return encoding

def to_unicode_2(text, module):
	if not text:
		return
		
	return text.decode(get_module_encoding(module), "replace")

def try_unicode(text, mod):
	if text is None: return ""
	encodings = ["utf8", "cp1252"]
	enc = get_module_encoding(mod)
	i = encodings.index(enc)
	try:
		return text.decode(enc)
	except UnicodeDecodeError:
		try:
			# ESV doesn't properly utf-8 copyright symbol in its about
			# so if we can't convert it to unicode, leave it as it is
			return text.decode(encodings[not i])
		except UnicodeDecodeError:
			return text.decode(enc, "replace")
	
