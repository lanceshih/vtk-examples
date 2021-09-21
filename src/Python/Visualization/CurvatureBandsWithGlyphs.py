#!/usr/bin/env python

import math
from collections import OrderedDict

import numpy as np
from vtk.util import numpy_support
from vtkmodules.numpy_interface import dataset_adapter as dsa
from vtkmodules.vtkCommonColor import (
    vtkColorSeries,
    vtkNamedColors
)
from vtkmodules.vtkCommonComputationalGeometry import (
    vtkParametricRandomHills,
    vtkParametricTorus
)
from vtkmodules.vtkCommonCore import (
    VTK_DOUBLE,
    vtkDoubleArray,
    vtkFloatArray,
    vtkIdList,
    vtkLookupTable,
    vtkPoints,
    vtkVariant,
    vtkVariantArray
)
from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkCommonTransforms import vtkTransform
from vtkmodules.vtkFiltersCore import (
    vtkCleanPolyData,
    vtkDelaunay2D,
    vtkElevationFilter,
    vtkFeatureEdges,
    vtkGlyph3D,
    vtkIdFilter,
    vtkMaskPoints,
    vtkPolyDataNormals,
    vtkReverseSense,
    vtkTriangleFilter
)
from vtkmodules.vtkFiltersGeneral import (
    vtkCurvatures,
    vtkTransformPolyDataFilter
)
from vtkmodules.vtkFiltersModeling import vtkBandedPolyDataContourFilter
from vtkmodules.vtkFiltersSources import (
    vtkArrowSource,
    vtkParametricFunctionSource,
    vtkPlaneSource,
    vtkSphereSource,
    vtkSuperquadricSource
)
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkInteractionWidgets import vtkCameraOrientationWidget
from vtkmodules.vtkRenderingAnnotation import vtkScalarBarActor
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkColorTransferFunction,
    vtkPolyDataMapper,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer
)


def main(argv):
    # ------------------------------------------------------------
    # Create the surface, lookup tables, contour filter etc.
    # ------------------------------------------------------------
    # desired_surface = 'Hills'
    # desired_surface = 'ParametricTorus'
    # desired_surface = 'Plane'
    desired_surface = 'RandomHills'
    # desired_surface = 'Sphere'
    # desired_surface = 'Torus'
    source = get_source(desired_surface)
    if not source:
        print('The surface is not available.')
        return

    # The length of the normal arrow glyphs.
    scale_factor = 1.0
    if desired_surface == 'Hills':
        scale_factor = 0.5
    elif desired_surface == 'Sphere':
        scale_factor = 2.0
    print(desired_surface)

    gaussian_curvature = True
    if gaussian_curvature:
        curvature = 'Gauss_Curvature'
    else:
        curvature = 'Mean_Curvature'

    cc = vtkCurvatures()
    cc.SetInputData(source)
    needs_adjusting = ['Hills', 'ParametricTorus', 'Plane', 'RandomHills', 'Torus']
    if gaussian_curvature:
        cc.SetCurvatureTypeToGaussian()
        cc.Update()
        if desired_surface in needs_adjusting:
            adjust_edge_curvatures(cc.GetOutput(), curvature)
        if desired_surface == 'Plane':
            constrain_curvatures(cc.GetOutput(), curvature, 0.0, 0.0)
        if desired_surface == 'Sphere':
            # Gaussian curvature is 1/r^2
            constrain_curvatures(cc.GetOutput(), curvature, 4.0, 4.0)
    else:
        cc.SetCurvatureTypeToMean()
        cc.Update()
        if desired_surface in needs_adjusting:
            adjust_edge_curvatures(cc.GetOutput(), curvature)
        if desired_surface == 'Plane':
            constrain_curvatures(cc.GetOutput(), curvature, 0.0, 0.0)
        if desired_surface == 'Sphere':
            # Mean curvature is 1/r
            constrain_curvatures(cc.GetOutput(), curvature, 2.0, 2.0)

    cc.GetOutput().GetPointData().SetActiveScalars(curvature)
    scalar_range_curvatures = cc.GetOutput().GetPointData().GetScalars(curvature).GetRange()
    scalar_range_elevation = cc.GetOutput().GetPointData().GetScalars('Elevation').GetRange()

    lut = get_categorical_lut()
    lut1 = get_diverging_lut()
    lut.SetTableRange(scalar_range_curvatures)
    lut1.SetTableRange(scalar_range_elevation)
    number_of_bands = lut.GetNumberOfTableValues()
    bands = get_bands(scalar_range_curvatures, number_of_bands, 10)
    if desired_surface == 'RandomHills':
        # These are my custom bands.
        # Generated by first running:
        # bands = get_bands(scalar_range_curvatures, number_of_bands, False)
        # then:
        #  freq = frequencies(bands, src)
        #  print_bands_frequencies(bands, freq)
        # Finally using the output to create this table:
        # my_bands = [
        #     [-0.630, -0.190], [-0.190, -0.043], [-0.043, -0.0136],
        #     [-0.0136, 0.0158], [0.0158, 0.0452], [0.0452, 0.0746],
        #     [0.0746, 0.104], [0.104, 0.251], [0.251, 1.131]]
        #  This demonstrates that the gaussian curvature of the surface
        #   is mostly planar with some hyperbolic regions (saddle points)
        #   and some spherical regions.
        my_bands = [
            [-0.630, -0.190], [-0.190, -0.043], [-0.043, 0.0452], [0.0452, 0.0746],
            [0.0746, 0.104], [0.104, 0.251], [0.251, 1.131]]
        # Comment this out if you want to see how allocating
        # equally spaced bands works.
        bands = get_custom_bands(scalar_range_curvatures, number_of_bands, my_bands)
        # Adjust the number of table values
        lut.SetNumberOfTableValues(len(bands))
    elif desired_surface == 'Hills':
        my_bands = [
            [-2.104, -0.15], [-0.15, -0.1], [-0.1, -0.05],
            [-0.05, -0.02], [-0.02, -0.005], [-0.005, -0.0005],
            [-0.0005, 0.0005], [0.0005, 0.09], [0.09, 4.972]]
        # Comment this out if you want to see how allocating
        # equally spaced bands works.
        bands = get_custom_bands(scalar_range_curvatures, number_of_bands, my_bands)
        # Adjust the number of table values
        lut.SetNumberOfTableValues(len(bands))

    # Let's do a frequency table.
    # The number of scalars in each band.
    freq = frequencies(bands, cc.GetOutput())
    bands, freq = adjust_ranges(bands, freq)
    print_bands_frequencies(bands, freq)

    lut.SetTableRange(scalar_range_curvatures)
    lut.SetNumberOfTableValues(len(bands))

    # We will use the midpoint of the band as the label.
    labels = []
    for k in bands:
        labels.append('{:4.2f}'.format(bands[k][1]))

    # Annotate
    values = vtkVariantArray()
    for i in range(len(labels)):
        values.InsertNextValue(vtkVariant(labels[i]))
    for i in range(values.GetNumberOfTuples()):
        lut.SetAnnotation(i, values.GetValue(i).ToString())

    # Create a lookup table with the colors reversed.
    lutr = reverse_lut(lut)

    # Create the contour bands.
    bcf = vtkBandedPolyDataContourFilter()
    bcf.SetInputData(cc.GetOutput())
    # Use either the minimum or maximum value for each band.
    for k in bands:
        bcf.SetValue(k, bands[k][2])
    # We will use an indexed lookup table.
    bcf.SetScalarModeToIndex()
    bcf.GenerateContourEdgesOn()

    # Generate the glyphs on the original surface.
    glyph = get_glyphs(cc.GetOutput(), scale_factor, False)

    # ------------------------------------------------------------
    # Create the mappers and actors
    # ------------------------------------------------------------

    colors = vtkNamedColors()

    # Set the background color.
    colors.SetColor('BkgColor', [179, 204, 255, 255])
    colors.SetColor("ParaViewBkg", [82, 87, 110, 255])

    src_mapper = vtkPolyDataMapper()
    src_mapper.SetInputConnection(bcf.GetOutputPort())
    src_mapper.SetScalarRange(scalar_range_curvatures)
    src_mapper.SetLookupTable(lut)
    src_mapper.SetScalarModeToUseCellData()

    src_actor = vtkActor()
    src_actor.SetMapper(src_mapper)

    # Create contour edges
    edge_mapper = vtkPolyDataMapper()
    edge_mapper.SetInputData(bcf.GetContourEdgesOutput())
    edge_mapper.SetResolveCoincidentTopologyToPolygonOffset()

    edge_actor = vtkActor()
    edge_actor.SetMapper(edge_mapper)
    edge_actor.GetProperty().SetColor(colors.GetColor3d('Black'))

    glyph_mapper = vtkPolyDataMapper()
    glyph_mapper.SetInputConnection(glyph.GetOutputPort())
    glyph_mapper.SetScalarModeToUsePointFieldData()
    glyph_mapper.SetColorModeToMapScalars()
    glyph_mapper.ScalarVisibilityOn()
    glyph_mapper.SelectColorArray('Elevation')
    # Colour by scalars.
    glyph_mapper.SetLookupTable(lut1)
    glyph_mapper.SetScalarRange(scalar_range_elevation)

    glyph_actor = vtkActor()
    glyph_actor.SetMapper(glyph_mapper)

    window_width = 800
    window_height = 800

    # Add scalar bars.
    scalar_bar = vtkScalarBarActor()
    # This LUT puts the lowest value at the top of the scalar bar.
    # scalar_bar->SetLookupTable(lut);
    # Use this LUT if you want the highest value at the top.
    scalar_bar.SetLookupTable(lutr)
    scalar_bar.SetTitle(curvature.replace('_', '\n'))
    scalar_bar.GetTitleTextProperty().SetColor(
        colors.GetColor3d('AliceBlue'))
    scalar_bar.GetLabelTextProperty().SetColor(
        colors.GetColor3d('AliceBlue'))
    scalar_bar.GetAnnotationTextProperty().SetColor(
        colors.GetColor3d('AliceBlue'))
    scalar_bar.UnconstrainedFontSizeOn()
    scalar_bar.SetMaximumWidthInPixels(window_width // 8)
    scalar_bar.SetMaximumHeightInPixels(window_height // 3)
    scalar_bar.SetPosition(0.85, 0.05)

    scalar_bar_elev = vtkScalarBarActor()
    # This LUT puts the lowest value at the top of the scalar bar.
    # scalar_bar_elev->SetLookupTable(lut);
    # Use this LUT if you want the highest value at the top.
    scalar_bar_elev.SetLookupTable(lut1)
    scalar_bar_elev.SetTitle('Elevation')
    scalar_bar_elev.GetTitleTextProperty().SetColor(
        colors.GetColor3d('AliceBlue'))
    scalar_bar_elev.GetLabelTextProperty().SetColor(
        colors.GetColor3d('AliceBlue'))
    scalar_bar_elev.GetAnnotationTextProperty().SetColor(
        colors.GetColor3d('AliceBlue'))
    scalar_bar_elev.UnconstrainedFontSizeOn()
    if desired_surface == 'Plane':
        scalar_bar_elev.SetNumberOfLabels(1)
    else:
        scalar_bar_elev.SetNumberOfLabels(5)
    scalar_bar_elev.SetMaximumWidthInPixels(window_width // 8)
    scalar_bar_elev.SetMaximumHeightInPixels(window_height // 3)
    # scalar_bar_elev.SetBarRatio(scalar_bar_elev.GetBarRatio() * 0.5)
    scalar_bar_elev.SetPosition(0.85, 0.4)

    # ------------------------------------------------------------
    # Create the RenderWindow, Renderer and Interactor
    # ------------------------------------------------------------
    ren = vtkRenderer()
    ren_win = vtkRenderWindow()
    iren = vtkRenderWindowInteractor()
    style = vtkInteractorStyleTrackballCamera()
    iren.SetInteractorStyle(style)

    ren_win.AddRenderer(ren)
    # Important: The interactor must be set prior to enabling the widget.
    iren.SetRenderWindow(ren_win)
    cam_orient_manipulator = vtkCameraOrientationWidget()
    cam_orient_manipulator.SetParentRenderer(ren)
    # Enable the widget.
    cam_orient_manipulator.On()

    # add actors
    ren.AddViewProp(src_actor)
    ren.AddViewProp(edge_actor)
    ren.AddViewProp(glyph_actor)
    ren.AddActor2D(scalar_bar)
    ren.AddActor2D(scalar_bar_elev)

    ren.SetBackground(colors.GetColor3d('ParaViewBkg'))
    ren_win.SetSize(window_width, window_height)
    ren_win.SetWindowName('CurvatureBandsWithGlyphs')

    if desired_surface == "RandomHills":
        camera = ren.GetActiveCamera()
        camera.SetPosition(10.9299, 59.1505, 24.9823)
        camera.SetFocalPoint(2.21692, 7.97545, 7.75135)
        camera.SetViewUp(-0.230136, 0.345504, -0.909761)
        camera.SetDistance(54.6966)
        camera.SetClippingRange(36.3006, 77.9852)
        ren_win.Render()

    iren.Start()


def get_custom_bands(d_r, number_of_bands, my_bands):
    """
    Divide a range into custom bands.

    You need to specify each band as an list [r1, r2] where r1 < r2 and
    append these to a list.
    The list should ultimately look
    like this: [[r1, r2], [r2, r3], [r3, r4]...]

    :param: d_r - [min, max] the range that is to be covered by the bands.
    :param: number_of_bands - the number of bands, a positive integer.
    :return: A dictionary consisting of band number and [min, midpoint, max] for each band.
    """
    bands = dict()
    if (d_r[1] < d_r[0]) or (number_of_bands <= 0):
        return bands
    x = my_bands
    # Determine the index of the range minimum and range maximum.
    idx_min = 0
    for idx in range(0, len(my_bands)):
        if my_bands[idx][1] > d_r[0] >= my_bands[idx][0]:
            idx_min = idx
            break

    idx_max = len(my_bands) - 1
    for idx in range(len(my_bands) - 1, -1, -1):
        if my_bands[idx][1] > d_r[1] >= my_bands[idx][0]:
            idx_max = idx
            break

    # Set the minimum to match the range minimum.
    x[idx_min][0] = d_r[0]
    x[idx_max][1] = d_r[1]
    x = x[idx_min: idx_max + 1]
    for idx, e in enumerate(x):
        bands[idx] = [e[0], e[0] + (e[1] - e[0]) / 2, e[1]]
    return bands


def frequencies(bands, src):
    """
    Count the number of scalars in each band.
    :param: bands - the bands.
    :param: src - the vtkPolyData source.
    :return: The frequencies of the scalars in each band.
    """
    freq = OrderedDict()
    for i in range(len(bands)):
        freq[i] = 0
    tuples = src.GetPointData().GetScalars().GetNumberOfTuples()
    for i in range(tuples):
        x = src.GetPointData().GetScalars().GetTuple1(i)
        for j in range(len(bands)):
            if x <= bands[j][2]:
                freq[j] = freq[j] + 1
                break
    return freq


def adjust_frequency_ranges(freq):
    """
    Get the indices of the first and last non-zero elements.
    :param freq: The frequency dictionary.
    :return: The indices of the first and last non-zero elements.
    """
    first = 0
    for k, v in freq.items():
        if v != 0:
            first = k
            break
    rev_keys = list(freq.keys())[::-1]
    last = rev_keys[0]
    for idx in list(freq.keys())[::-1]:
        if freq[idx] != 0:
            last = idx
            break
    return first, last


def get_elevations(src):
    """
    Generate elevations over the surface.
    :param: src - the vtkPolyData source.
    :return: - vtkPolyData source with elevations.
    """
    bounds = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    src.GetBounds(bounds)
    if abs(bounds[2]) < 1.0e-8 and abs(bounds[3]) < 1.0e-8:
        bounds[3] = bounds[2] + 1
    elev_filter = vtkElevationFilter()
    elev_filter.SetInputData(src)
    elev_filter.SetLowPoint(0, bounds[2], 0)
    elev_filter.SetHighPoint(0, bounds[3], 0)
    elev_filter.SetScalarRange(bounds[2], bounds[3])
    elev_filter.Update()
    return elev_filter.GetPolyDataOutput()


def get_hills():
    # Create four hills on a plane.
    # This will have regions of negative, zero and positive Gsaussian curvatures.

    x_res = 50
    y_res = 50
    x_min = -5.0
    x_max = 5.0
    dx = (x_max - x_min) / (x_res - 1)
    y_min = -5.0
    y_max = 5.0
    dy = (y_max - y_min) / (x_res - 1)

    # Make a grid.
    points = vtkPoints()
    for i in range(0, x_res):
        x = x_min + i * dx
        for j in range(0, y_res):
            y = y_min + j * dy
            points.InsertNextPoint(x, y, 0)

    # Add the grid points to a polydata object.
    plane = vtkPolyData()
    plane.SetPoints(points)

    # Triangulate the grid.
    delaunay = vtkDelaunay2D()
    delaunay.SetInputData(plane)
    delaunay.Update()

    polydata = delaunay.GetOutput()

    elevation = vtkDoubleArray()
    elevation.SetNumberOfTuples(points.GetNumberOfPoints())

    #  We define the parameters for the hills here.
    # [[0: x0, 1: y0, 2: x variance, 3: y variance, 4: amplitude]...]
    hd = [[-2.5, -2.5, 2.5, 6.5, 3.5], [2.5, 2.5, 2.5, 2.5, 2],
          [5.0, -2.5, 1.5, 1.5, 2.5], [-5.0, 5, 2.5, 3.0, 3]]
    xx = [0.0] * 2
    for i in range(0, points.GetNumberOfPoints()):
        x = list(polydata.GetPoint(i))
        for j in range(0, len(hd)):
            xx[0] = (x[0] - hd[j][0] / hd[j][2]) ** 2.0
            xx[1] = (x[1] - hd[j][1] / hd[j][3]) ** 2.0
            x[2] += hd[j][4] * math.exp(-(xx[0] + xx[1]) / 2.0)
            polydata.GetPoints().SetPoint(i, x)
            elevation.SetValue(i, x[2])

    textures = vtkFloatArray()
    textures.SetNumberOfComponents(2)
    textures.SetNumberOfTuples(2 * polydata.GetNumberOfPoints())
    textures.SetName("Textures")

    for i in range(0, x_res):
        tc = [i / (x_res - 1.0), 0.0]
        for j in range(0, y_res):
            # tc[1] = 1.0 - j / (y_res - 1.0)
            tc[1] = j / (y_res - 1.0)
            textures.SetTuple(i * y_res + j, tc)

    polydata.GetPointData().SetScalars(elevation)
    polydata.GetPointData().GetScalars().SetName("Elevation")
    polydata.GetPointData().SetTCoords(textures)

    normals = vtkPolyDataNormals()
    normals.SetInputData(polydata)
    normals.SetInputData(polydata)
    normals.SetFeatureAngle(30)
    normals.SplittingOff()

    tr1 = vtkTransform()
    tr1.RotateX(-90)

    tf1 = vtkTransformPolyDataFilter()
    tf1.SetInputConnection(normals.GetOutputPort())
    tf1.SetTransform(tr1)
    tf1.Update()

    return tf1.GetOutput()


def get_parametric_hills():
    """
    Make a parametric hills surface as the source.
    :return: vtkPolyData with normal and scalar data.
    """
    fn = vtkParametricRandomHills()
    fn.AllowRandomGenerationOn()
    fn.SetRandomSeed(1)
    fn.SetNumberOfHills(30)
    # Make the normals face out of the surface.
    # Not needed with VTK 8.0 or later.
    # if fn.GetClassName() == 'vtkParametricRandomHills':
    #    fn.ClockwiseOrderingOff()

    source = vtkParametricFunctionSource()
    source.SetParametricFunction(fn)
    source.SetUResolution(50)
    source.SetVResolution(50)
    source.SetScalarModeToZ()
    source.Update()
    # Name the arrays (not needed in VTK 6.2+ for vtkParametricFunctionSource).
    # source.GetOutput().GetPointData().GetNormals().SetName('Normals')
    # source.GetOutput().GetPointData().GetScalars().SetName('Scalars')
    # Rename the scalars to 'Elevation' since we are using the Z-scalars as elevations.
    source.GetOutput().GetPointData().GetScalars().SetName('Elevation')

    transform = vtkTransform()
    transform.Translate(0.0, 5.0, 15.0)
    transform.RotateX(-90.0)
    transform_filter = vtkTransformPolyDataFilter()
    transform_filter.SetInputConnection(source.GetOutputPort())
    transform_filter.SetTransform(transform)
    transform_filter.Update()

    return transform_filter.GetOutput()


def get_parametric_torus():
    """
    Make a parametric torus as the source.
    :return: vtkPolyData with normal and scalar data.
    """

    fn = vtkParametricTorus()
    fn.SetRingRadius(5)
    fn.SetCrossSectionRadius(2)

    source = vtkParametricFunctionSource()
    source.SetParametricFunction(fn)
    source.SetUResolution(50)
    source.SetVResolution(50)
    source.SetScalarModeToZ()
    source.Update()

    # Name the arrays (not needed in VTK 6.2+ for vtkParametricFunctionSource).
    # source.GetOutput().GetPointData().GetNormals().SetName('Normals')
    # source.GetOutput().GetPointData().GetScalars().SetName('Scalars')
    # Rename the scalars to 'Elevation' since we are using the Z-scalars as elevations.
    source.GetOutput().GetPointData().GetScalars().SetName('Elevation')

    transform = vtkTransform()
    transform.RotateX(-90.0)
    transform_filter = vtkTransformPolyDataFilter()
    transform_filter.SetInputConnection(source.GetOutputPort())
    transform_filter.SetTransform(transform)
    transform_filter.Update()

    return transform_filter.GetOutput()


def get_plane():
    """
    Make a plane as the source.
    :return: vtkPolyData with normal and scalar data.
    """

    source = vtkPlaneSource()
    source.SetOrigin(-10.0, -10.0, 0.0)
    source.SetPoint2(-10.0, 10.0, 0.0)
    source.SetPoint1(10.0, -10.0, 0.0)
    source.SetXResolution(20)
    source.SetYResolution(20)
    source.Update()

    transform = vtkTransform()
    transform.Translate(0.0, 0.0, 0.0)
    transform.RotateX(-90.0)
    transform_filter = vtkTransformPolyDataFilter()
    transform_filter.SetInputConnection(source.GetOutputPort())
    transform_filter.SetTransform(transform)
    transform_filter.Update()

    # We have a m x n array of quadrilaterals arranged as a regular tiling in a
    # plane. So pass it through a triangle filter since the curvature filter only
    # operates on polys.
    tri = vtkTriangleFilter()
    tri.SetInputConnection(transform_filter.GetOutputPort())

    # Pass it though a CleanPolyDataFilter and merge any points which
    # are coincident, or very close
    cleaner = vtkCleanPolyData()
    cleaner.SetInputConnection(tri.GetOutputPort())
    cleaner.SetTolerance(0.005)
    cleaner.Update()

    return cleaner.GetOutput()


def get_sphere():
    source = vtkSphereSource()
    source.SetCenter(0.0, 0.0, 0.0)
    source.SetRadius(10.0)
    source.SetThetaResolution(32)
    source.SetPhiResolution(32)
    source.Update()

    return source.GetOutput()


def get_torus():
    """
    Make a torus as the source.
    :return: vtkPolyData with normal and scalar data.
    """
    source = vtkSuperquadricSource()
    source.SetCenter(0.0, 0.0, 0.0)
    source.SetScale(1.0, 1.0, 1.0)
    source.SetPhiResolution(64)
    source.SetThetaResolution(64)
    source.SetThetaRoundness(1)
    source.SetThickness(0.5)
    source.SetSize(10)
    source.SetToroidal(1)

    # The quadric is made of strips, so pass it through a triangle filter as
    # the curvature filter only operates on polys
    tri = vtkTriangleFilter()
    tri.SetInputConnection(source.GetOutputPort())

    # The quadric has nasty discontinuities from the way the edges are generated
    # so let's pass it though a CleanPolyDataFilter and merge any points which
    # are coincident, or very close
    cleaner = vtkCleanPolyData()
    cleaner.SetInputConnection(tri.GetOutputPort())
    cleaner.SetTolerance(0.005)
    cleaner.Update()

    return cleaner.GetOutput()


def adjust_edge_curvatures(source, curvature_name, epsilon=1.0e-08):
    """
    This function adjusts curvatures along the edges of the surface by replacing
     the value with the average value of the curvatures of points in the neighborhood.

    Remember to update the vtkCurvatures object before calling this.

    :param source: A vtkPolyData object corresponding to the vtkCurvatures object.
    :param curvature_name: The name of the curvature, 'Gauss_Curvature' or 'Mean_Curvature'.
    :param epsilon: Absolute curvature values less than this will be set to zero.
    :return:
    """

    def point_neighbourhood(pt_id):
        """
        Find the ids of the neighbours of pt_id.

        :param pt_id: The point id.
        :return: The neighbour ids.
        """
        """
        Extract the topological neighbors for point pId. In two steps:
        1) source.GetPointCells(pt_id, cell_ids)
        2) source.GetCellPoints(cell_id, cell_point_ids) for all cell_id in cell_ids
        """
        cell_ids = vtkIdList()
        source.GetPointCells(pt_id, cell_ids)
        neighbour = set()
        for cell_idx in range(0, cell_ids.GetNumberOfIds()):
            cell_id = cell_ids.GetId(cell_idx)
            cell_point_ids = vtkIdList()
            source.GetCellPoints(cell_id, cell_point_ids)
            for cell_pt_idx in range(0, cell_point_ids.GetNumberOfIds()):
                neighbour.add(cell_point_ids.GetId(cell_pt_idx))
        return neighbour

    def compute_distance(pt_id_a, pt_id_b):
        """
        Compute the distance between two points given their ids.

        :param pt_id_a:
        :param pt_id_b:
        :return:
        """
        pt_a = np.array(source.GetPoint(pt_id_a))
        pt_b = np.array(source.GetPoint(pt_id_b))
        return np.linalg.norm(pt_a - pt_b)

    # Get the active scalars
    source.GetPointData().SetActiveScalars(curvature_name)
    np_source = dsa.WrapDataObject(source)
    curvatures = np_source.PointData[curvature_name]

    #  Get the boundary point IDs.
    array_name = 'ids'
    id_filter = vtkIdFilter()
    id_filter.SetInputData(source)
    id_filter.SetPointIds(True)
    id_filter.SetCellIds(False)
    id_filter.SetPointIdsArrayName(array_name)
    id_filter.SetCellIdsArrayName(array_name)
    id_filter.Update()

    edges = vtkFeatureEdges()
    edges.SetInputConnection(id_filter.GetOutputPort())
    edges.BoundaryEdgesOn()
    edges.ManifoldEdgesOff()
    edges.NonManifoldEdgesOff()
    edges.FeatureEdgesOff()
    edges.Update()

    edge_array = edges.GetOutput().GetPointData().GetArray(array_name)
    boundary_ids = []
    for i in range(edges.GetOutput().GetNumberOfPoints()):
        boundary_ids.append(edge_array.GetValue(i))
    # Remove duplicate Ids.
    p_ids_set = set(boundary_ids)

    # Iterate over the edge points and compute the curvature as the weighted
    # average of the neighbours.
    count_invalid = 0
    for p_id in boundary_ids:
        p_ids_neighbors = point_neighbourhood(p_id)
        # Keep only interior points.
        p_ids_neighbors -= p_ids_set
        # Compute distances and extract curvature values.
        curvs = [curvatures[p_id_n] for p_id_n in p_ids_neighbors]
        dists = [compute_distance(p_id_n, p_id) for p_id_n in p_ids_neighbors]
        curvs = np.array(curvs)
        dists = np.array(dists)
        curvs = curvs[dists > 0]
        dists = dists[dists > 0]
        if len(curvs) > 0:
            weights = 1 / np.array(dists)
            weights /= weights.sum()
            new_curv = np.dot(curvs, weights)
        else:
            # Corner case.
            count_invalid += 1
            # Assuming the curvature of the point is planar.
            new_curv = 0.0
        # Set the new curvature value.
        curvatures[p_id] = new_curv

    #  Set small values to zero.
    if epsilon != 0.0:
        curvatures = np.where(abs(curvatures) < epsilon, 0, curvatures)
        # Curvatures is now an ndarray
        curv = numpy_support.numpy_to_vtk(num_array=curvatures.ravel(),
                                          deep=True,
                                          array_type=VTK_DOUBLE)
        curv.SetName(curvature_name)
        source.GetPointData().RemoveArray(curvature_name)
        source.GetPointData().AddArray(curv)
        source.GetPointData().SetActiveScalars(curvature_name)


def constrain_curvatures(source, curvature_name, lower_bound=0.0, upper_bound=0.0):
    """
    This function constrains curvatures to the range [lower_bound ... upper_bound].

    Remember to update the vtkCurvatures object before calling this.

    :param source: A vtkPolyData object corresponding to the vtkCurvatures object.
    :param curvature_name: The name of the curvature, 'Gauss_Curvature' or 'Mean_Curvature'.
    :param lower_bound: The lower bound.
    :param upper_bound: The upper bound.
    :return:
    """

    bounds = list()
    if lower_bound < upper_bound:
        bounds.append(lower_bound)
        bounds.append(upper_bound)
    else:
        bounds.append(upper_bound)
        bounds.append(lower_bound)

    # Get the active scalars
    source.GetPointData().SetActiveScalars(curvature_name)
    np_source = dsa.WrapDataObject(source)
    curvatures = np_source.PointData[curvature_name]

    # Set upper and lower bounds.
    curvatures = np.where(curvatures < bounds[0], bounds[0], curvatures)
    curvatures = np.where(curvatures > bounds[1], bounds[1], curvatures)
    # Curvatures is now an ndarray
    curv = numpy_support.numpy_to_vtk(num_array=curvatures.ravel(),
                                      deep=True,
                                      array_type=VTK_DOUBLE)
    curv.SetName(curvature_name)
    source.GetPointData().RemoveArray(curvature_name)
    source.GetPointData().AddArray(curv)
    source.GetPointData().SetActiveScalars(curvature_name)


def get_color_series():
    color_series = vtkColorSeries()
    # Select a color scheme.
    # color_series_enum = color_series.BREWER_DIVERGING_BROWN_BLUE_GREEN_9
    # color_series_enum = color_series.BREWER_DIVERGING_SPECTRAL_10
    # color_series_enum = color_series.BREWER_DIVERGING_SPECTRAL_3
    # color_series_enum = color_series.BREWER_DIVERGING_PURPLE_ORANGE_9
    # color_series_enum = color_series.BREWER_SEQUENTIAL_BLUE_PURPLE_9
    # color_series_enum = color_series.BREWER_SEQUENTIAL_BLUE_GREEN_9
    color_series_enum = color_series.BREWER_QUALITATIVE_SET3
    # color_series_enum = color_series.CITRUS
    color_series.SetColorScheme(color_series_enum)
    return color_series


def get_categorical_lut():
    """
    Make a lookup table using vtkColorSeries.
    :return: An indexed (categorical) lookup table.
    """
    color_series = get_color_series()
    # Make the lookup table.
    lut = vtkLookupTable()
    color_series.BuildLookupTable(lut, color_series.CATEGORICAL)
    lut.SetNanColor(0, 0, 0, 1)
    return lut


def get_ordinal_lut():
    """
    Make a lookup table using vtkColorSeries.
    :return: An ordinal (not indexed) lookup table.
    """
    color_series = get_color_series()
    # Make the lookup table.
    lut = vtkLookupTable()
    color_series.BuildLookupTable(lut, color_series.ORDINAL)
    lut.SetNanColor(0, 0, 0, 1)
    return lut


def get_diverging_lut():
    """
    See: [Diverging Color Maps for Scientific Visualization](https://www.kennethmoreland.com/color-maps/)
                       start point         midPoint            end point
     cool to warm:     0.230, 0.299, 0.754 0.865, 0.865, 0.865 0.706, 0.016, 0.150
     purple to orange: 0.436, 0.308, 0.631 0.865, 0.865, 0.865 0.759, 0.334, 0.046
     green to purple:  0.085, 0.532, 0.201 0.865, 0.865, 0.865 0.436, 0.308, 0.631
     blue to brown:    0.217, 0.525, 0.910 0.865, 0.865, 0.865 0.677, 0.492, 0.093
     green to red:     0.085, 0.532, 0.201 0.865, 0.865, 0.865 0.758, 0.214, 0.233

    :return:
    """
    ctf = vtkColorTransferFunction()
    ctf.SetColorSpaceToDiverging()
    # Cool to warm.
    ctf.AddRGBPoint(0.0, 0.085, 0.532, 0.201)
    ctf.AddRGBPoint(0.5, 0.865, 0.865, 0.865)
    ctf.AddRGBPoint(1.0, 0.758, 0.214, 0.233)

    table_size = 256
    lut = vtkLookupTable()
    lut.SetNumberOfTableValues(table_size)
    lut.Build()

    for i in range(0, table_size):
        rgba = list(ctf.GetColor(float(i) / table_size))
        rgba.append(1)
        lut.SetTableValue(i, rgba)

    return lut


def reverse_lut(lut):
    """
    Create a lookup table with the colors reversed.
    :param: lut - An indexed lookup table.
    :return: The reversed indexed lookup table.
    """
    lutr = vtkLookupTable()
    lutr.DeepCopy(lut)
    t = lut.GetNumberOfTableValues() - 1
    rev_range = reversed(list(range(t + 1)))
    for i in rev_range:
        rgba = [0.0] * 3
        v = float(i)
        lut.GetColor(v, rgba)
        rgba.append(lut.GetOpacity(v))
        lutr.SetTableValue(t - i, rgba)
    t = lut.GetNumberOfAnnotatedValues() - 1
    rev_range = reversed(list(range(t + 1)))
    for i in rev_range:
        lutr.SetAnnotation(t - i, lut.GetAnnotation(i))
    return lutr


def get_glyphs(src, scale_factor=1.0, reverse_normals=False):
    """
    Glyph the normals on the surface.

    You may need to adjust the parameters for mask_pts, arrow and glyph for a
    nice appearance.

    :param: src - the surface to glyph.
    :param: reverse_normals - if True the normals on the surface are reversed.
    :return: The glyph object.

    """
    # Sometimes the contouring algorithm can create a volume whose gradient
    # vector and ordering of polygon (using the right hand rule) are
    # inconsistent. vtkReverseSense cures this problem.
    reverse = vtkReverseSense()

    # Choose a random subset of points.
    mask_pts = vtkMaskPoints()
    mask_pts.SetOnRatio(5)
    mask_pts.RandomModeOn()
    if reverse_normals:
        reverse.SetInputData(src)
        reverse.ReverseCellsOn()
        reverse.ReverseNormalsOn()
        mask_pts.SetInputConnection(reverse.GetOutputPort())
    else:
        mask_pts.SetInputData(src)

    # Source for the glyph filter
    arrow = vtkArrowSource()
    arrow.SetTipResolution(16)
    arrow.SetTipLength(0.3)
    arrow.SetTipRadius(0.1)

    glyph = vtkGlyph3D()
    glyph.SetSourceConnection(arrow.GetOutputPort())
    glyph.SetInputConnection(mask_pts.GetOutputPort())
    glyph.SetVectorModeToUseNormal()
    glyph.SetScaleFactor(scale_factor)
    glyph.SetColorModeToColorByVector()
    glyph.SetScaleModeToScaleByVector()
    glyph.OrientOn()
    glyph.Update()
    return glyph


def get_source(source):
    surface = source.lower()
    available_surfaces = ['hills', 'parametrictorus', 'plane', 'randomhills', 'sphere', 'torus']
    if surface not in available_surfaces:
        return None
    elif surface == 'hills':
        return get_hills()
    elif surface == 'parametrictorus':
        return get_parametric_torus()
    elif surface == 'plane':
        return get_elevations(get_plane())
    elif surface == 'randomhills':
        return get_parametric_hills()
    elif surface == 'sphere':
        return get_elevations(get_sphere())
    elif surface == 'torus':
        return get_elevations(get_torus())
    return None


def get_bands(d_r, number_of_bands, precision=2, nearest_integer=False):
    """
    Divide a range into bands
    :param: d_r - [min, max] the range that is to be covered by the bands.
    :param: number_of_bands - The number of bands, a positive integer.
    :param: precision - The decimal precision of the bounds.
    :param: nearest_integer - If True then [floor(min), ceil(max)] is used.
    :return: A dictionary consisting of the band number and [min, midpoint, max] for each band.
    """
    prec = abs(precision)
    if prec > 14:
        prec = 14

    bands = dict()
    if (d_r[1] < d_r[0]) or (number_of_bands <= 0):
        return bands
    x = list(d_r)
    if nearest_integer:
        x[0] = math.floor(x[0])
        x[1] = math.ceil(x[1])
    dx = (x[1] - x[0]) / float(number_of_bands)
    b = [x[0], x[0] + dx / 2.0, x[0] + dx]
    i = 0
    while i < number_of_bands:
        b = list(map(lambda ele_b: round(ele_b, prec), b))
        if i == 0:
            b[0] = x[0]
        bands[i] = b
        b = [b[0] + dx, b[1] + dx, b[2] + dx]
        i += 1
    return bands


def get_frequencies(bands, src):
    """
    Count the number of scalars in each band.
    The scalars used are the active scalars in the polydata.

    :param: bands - The bands.
    :param: src - The vtkPolyData source.
    :return: The frequencies of the scalars in each band.
    """
    freq = dict()
    for i in range(len(bands)):
        freq[i] = 0
    tuples = src.GetPointData().GetScalars().GetNumberOfTuples()
    for i in range(tuples):
        x = src.GetPointData().GetScalars().GetTuple1(i)
        for j in range(len(bands)):
            if x <= bands[j][2]:
                freq[j] += 1
                break
    return freq


def adjust_ranges(bands, freq):
    """
    The bands and frequencies are adjusted so that the first and last
     frequencies in the range are non-zero.
    :param bands: The bands dictionary.
    :param freq: The frequency dictionary.
    :return: Adjusted bands and frequencies.
    """
    # Get the indices of the first and last non-zero elements.
    first = 0
    for k, v in freq.items():
        if v != 0:
            first = k
            break
    rev_keys = list(freq.keys())[::-1]
    last = rev_keys[0]
    for idx in list(freq.keys())[::-1]:
        if freq[idx] != 0:
            last = idx
            break
    # Now adjust the ranges.
    min_key = min(freq.keys())
    max_key = max(freq.keys())
    for idx in range(min_key, first):
        freq.pop(idx)
        bands.pop(idx)
    for idx in range(last + 1, max_key + 1):
        freq.popitem()
        bands.popitem()
    old_keys = freq.keys()
    adj_freq = dict()
    adj_bands = dict()

    for idx, k in enumerate(old_keys):
        adj_freq[idx] = freq[k]
        adj_bands[idx] = bands[k]

    return adj_bands, adj_freq


def print_bands_frequencies(bands, freq, precision=2):
    prec = abs(precision)
    if prec > 14:
        prec = 14

    if len(bands) != len(freq):
        print('Bands and Frequencies must be the same size.')
        return
    s = f'Bands & Frequencies:\n'
    total = 0
    width = prec + 6
    for k, v in bands.items():
        total += freq[k]
        for j, q in enumerate(v):
            if j == 0:
                s += f'{k:4d} ['
            if j == len(v) - 1:
                s += f'{q:{width}.{prec}f}]: {freq[k]:8d}\n'
            else:
                s += f'{q:{width}.{prec}f}, '
    width = 3 * width + 13
    s += f'{"Total":{width}s}{total:8d}\n'
    print(s)


if __name__ == '__main__':
    import sys

    main(sys.argv)
