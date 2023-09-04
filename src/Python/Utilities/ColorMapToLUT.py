#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersCore import vtkElevationFilter
from vtkmodules.vtkFiltersSources import vtkConeSource, vtkSphereSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDiscretizableColorTransferFunction,
    vtkPolyDataMapper,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer
)


def main():
    colors = vtkNamedColors()
    colors.SetColor('ParaViewBkg', 82, 87, 110, 255)

    ren = vtkRenderer()
    ren.SetBackground(colors.GetColor3d('ParaViewBkg'))
    ren_win = vtkRenderWindow()
    ren_win.SetSize(640, 480)
    ren_win.SetWindowName('ColorMapToLUT')
    ren_win.AddRenderer(ren)
    iren = vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)

    style = vtkInteractorStyleTrackballCamera()
    iren.SetInteractorStyle(style)

    sphere = vtkSphereSource()
    sphere.SetThetaResolution(64)
    sphere.SetPhiResolution(32)

    cone = vtkConeSource()
    cone.SetResolution(6)
    cone.SetDirection(0, 1, 0)
    cone.SetHeight(1)
    cone.Update()
    bounds = cone.GetOutput().GetBounds()

    elevation_filter = vtkElevationFilter()
    elevation_filter.SetLowPoint(0, bounds[2], 0)
    elevation_filter.SetHighPoint(0, bounds[3], 0)
    elevation_filter.SetInputConnection(cone.GetOutputPort())
    # elevation_filter.SetInputConnection(sphere.GetOutputPort())

    ctf = get_ctf()

    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(elevation_filter.GetOutputPort())
    mapper.SetLookupTable(ctf)
    mapper.SetColorModeToMapScalars()
    mapper.InterpolateScalarsBeforeMappingOn()

    actor = vtkActor()
    actor.SetMapper(mapper)

    ren.AddActor(actor)

    ren_win.Render()
    iren.Start()


def get_ctf():
    # name: Fast, creator: Francesca Samsel, file name: Fast.xml
    ctf = vtkDiscretizableColorTransferFunction()

    ctf.SetColorSpaceToLab()
    ctf.SetScaleToLinear()

    ctf.SetNanColor(0, 0, 0)

    ctf.AddRGBPoint(0, 0.08800000000000002, 0.18810000000000007, 0.55)
    ctf.AddRGBPoint(0.16144, 0.21989453864645603, 0.5170512023315895, 0.7093372214401806)
    ctf.AddRGBPoint(0.351671, 0.5048913252297864, 0.8647869538833338, 0.870502284878942)
    ctf.AddRGBPoint(0.501285, 1, 1, 0.83)
    ctf.AddRGBPoint(0.620051, 0.9418960444346476, 0.891455547964053, 0.5446035798119958)
    ctf.AddRGBPoint(0.835408342528245, 0.75, 0.44475, 0.255)
    ctf.AddRGBPoint(1, 0.56, 0.055999999999999994, 0.055999999999999994)

    ctf.SetNumberOfValues(7)
    ctf.DiscretizeOn()

    return ctf


if __name__ == '__main__':
    main()
