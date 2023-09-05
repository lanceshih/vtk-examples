### Description

Demonstrate a cone using the vtkDiscretizableColorTransferFunction to generate the colormap.

The Python programs:

- [ColorMapToLUT_XML](../ColorMapToLUT_XML/)
- [ColorMapToLUT_JSON](../ColorMapToLUT_JSON/)

 can be used to generate the following function from either an XML description of a colormap or a JSON one:

``` Python
def get_ctf():
    ...
    return ctf
```

Feel free to use either of these programs to generate different colormaps until you find one you like.

A good initial source for color maps is: [SciVisColor](https://sciviscolor.org/) -- this will provide you with plenty of XML examples.
