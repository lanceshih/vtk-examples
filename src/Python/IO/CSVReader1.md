### Description

This example loads a CSV file, edits it and visualises the result.

It demonstrates the use of [pandas](https://pandas.pydata.org/) to read and edit the CSV input file, then create a temporary file containing the desired columns. This temporary file is subsequently read and parsed using vtkDelimitedTextReader.

The key thing about `pandas` is it can read/write data in various formats: CSV and text files, Microsoft Excel, SQL databases, and the fast HDF5 format. It is highly optimized for performance and the DataFrame object allows for extensive row/column manipulation. So we can edit the data, creating new columns, and, finally, select only relevant columns for further analysis by VTK.

In this case we create a CSV file of selected columns and read this with vtkDelimitedTextReader.

The files used to generate the example are:

``` text
<DATA>/LakeGininderra.csv
<DATA>/LakeGininderra.kmz
```

Where:

- `<DATA>` is the path to `?vtk-?examples/src/Testing/Data`
- `LakeGininderra.csv` is the CSV file used by this program.
- `LakeGininderra.kmz` can be loaded into Google Earth to display the track.

The parameters for typical usage are something like this:

``` text
<DATA>/LakeGininderra.csv -u -oLakeGininderraTrack -pResults
```

<figure>
  <img style="float:middle" src="https://raw.githubusercontent.com/Kitware/vtk-examples/gh-pages/src/SupplementaryData/Python/IO/LakeGininderra.jpg">
  <figcaption>A Google Earth image of the track.</figcaption>
</figure>

Further information:

- This example was inspired by [Easy Data Conversion to VTK with Python](https://www.kitware.com/easy-data-conversion-to-vtk-with-python/).
- See [Installing pandas](https://pandas.pydata.org/docs/getting_started/install.html).
