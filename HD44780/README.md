# Driver for character-based LCD displays

This driver is for displays based on the Hitachi HD44780 driver: these are
widely available, typically in 16 character x 2 rows format.

# Files

 * `alcd.py` Driver, includes connection details.
 * `alcdtest.py` Test/demo script.

Currently most of the documentation, including wiring details, is in the code.

# Display Formatting

The driver represents an LCD display as an array indexed by row. Assigning a
string to a row causes that row to be updated. To write text to a specific
column of the display it is recommended to use the Python string `format`
method.

For exampls this function formats a string such that it is left-padded with
spaces to a given column and right-padded to the specified width (typically the
width of the display). This ensures previous contents are overwritten.

```python
def print_at(st, col, width=16):
    return '{:>{col}s}{:{t}s}'.format(st,'', col=col+len(st), t = width-(col+len(st)))
```

```
>>> print_at('cat', 2)
'  cat           '
>>> len(_)
16
>>> 
```

Similar use of the `format` method can be used to achieve more complex
tabulated data layouts.
