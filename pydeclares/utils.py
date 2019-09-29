import inspect


def tuple_str(obj_name, fields):
	# Return a string representing each field of obj_name as a tuple
	# member.  So, if fields is ['x', 'y'] and obj_name is "self",
	# return "(self.x,self.y)".

	# Special case for the 0-tuple.
	if not fields:
		return '()'
	# Note the trailing comma, needed if this turns out to be a 1-tuple.
	return f'({",".join([f"{obj_name}.{f.name}" for f in fields])},)'


def isinstance_safe(o, t):
	try:
		result = isinstance(o, t)
	except Exception:
		return False
	else:
		return result


def issubclass_safe(cls, classinfo):
	try:
		return issubclass(cls, classinfo)
	except Exception:
		return (is_new_type_subclass_safe(cls, classinfo) if is_new_type(cls) else False)


def is_new_type_subclass_safe(cls, classinfo):
	super_type = getattr(cls, "__supertype__", None)

	if super_type:
		return is_new_type_subclass_safe(super_type, classinfo)

	try:
		return issubclass(cls, classinfo)
	except Exception:
		return False


def is_new_type(type_):
	return inspect.isfunction(type_) and hasattr(type_, "__supertype__")
