### Description

Generate a VTK colormap from an XML description of a colormap.

A cone is rendered to demonstrate the resultant colormap. C++ and Python functions can also be generated which implement the colormap. These can be copied into [ColorMapToLUT.cxx]() or [ColorMapToLUT.py]() or into your own code.

This program was inspired by this discussion: [Replacement default color map and background palette](https://discourse.paraview.org/t/replacement-default-color-map-and-background-palette/12712), and,  the **Fast** colormap from this discussion is used as test data here.

A good initial source for color maps is: [SciVisColor](https://sciviscolor.org/) -- this will provide you with plenty of XML examples.

**Note:** 

- The XML parser is [lxml](https://lxml.de/)
- Currently the parsing only works for colormaps with no Section key.

Further information:

- [VTK Examples - Some ColorMap to LookupTable tools]()
- [How to export ParaView colormap into a format that could be read by matplotlib](https://discourse.paraview.org/t/how-to-export-paraview-colormap-into-a-format-that-could-be-read-by-matplotlib/2436)
- [How to export ParaView colormap into a format that could be read by matplotlib?](https://discourse.paraview.org/t/how-to-export-paraview-colormap-into-a-format-that-could-be-read-by-matplotlib/2394)
- [Color map advice and resources](https://discourse.paraview.org/t/color-map-advice-and-resources/6452/4)
