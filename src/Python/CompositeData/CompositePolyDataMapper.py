#!/usr/bin/env python

# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet
from vtkmodules.vtkFiltersSources import vtkSphereSource
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkCompositeDataDisplayAttributes,
    vtkCompositePolyDataMapper,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer
)


def main():
    colors = vtkNamedColors()

    # Create Sphere 1.
    sphere1 = vtkSphereSource()
    sphere1.SetRadius(3)
    sphere1.SetCenter(0, 0, 0)
    sphere1.Update()

    # Create Sphere 2.
    sphere2 = vtkSphereSource()
    sphere2.SetRadius(2)
    sphere2.SetCenter(2, 0, 0)
    sphere2.Update()

    mbds = vtkMultiBlockDataSet()
    mbds.SetNumberOfBlocks(3)
    mbds.SetBlock(0, sphere1.GetOutput())
    # Leave block 1 NULL.  NULL blocks are valid and should be handled by
    # algorithms that process multiblock datasets.  Especially when
    # running in parallel where the blocks owned by other processes are
    # NULL in this process.
    mbds.SetBlock(2, sphere2.GetOutput())

    # Use vtkCompositePolyDataMapper2 if VTK Version < 90020230516
    mapper = vtkCompositePolyDataMapper()
    mapper.SetInputDataObject(mbds)
    cdsa = vtkCompositeDataDisplayAttributes()
    mapper.SetCompositeDataDisplayAttributes(cdsa)

    # You can use the vtkCompositeDataDisplayAttributes to set the color,
    # opacity and visibiliy of individual blocks of the multiblock dataset.
    # Attributes are mapped by block pointers (vtkDataObject*), so these can
    # be queried by their flat index through a convenience function in the
    # attribute class (vtkCompositeDataDisplayAttributes::DataObjectFromIndex).
    # Alternatively, one can set attributes directly through the mapper using
    # flat indices.
    #
    # This sets the block at flat index 3 red
    # Note that the index is the flat index in the tree, so the whole multiblock
    # is index 0 and the blocks are flat indexes 1, 2 and 3.  This affects
    # the block returned by mbds.GetBlock(2).
    mapper.SetBlockColor(3, colors.GetColor3d('Red'))
    # Color the spheres.
    mapper.SetBlockColor(1, colors.GetColor3d('LavenderBlush'))
    mapper.SetBlockColor(2, colors.GetColor3d('Lavender'))

    actor = vtkActor()
    actor.SetMapper(mapper)

    # Create the Renderer, RenderWindow, and RenderWindowInteractor.
    renderer = vtkRenderer()
    renderWindow = vtkRenderWindow()
    renderWindow.AddRenderer(renderer)
    renderWindowInteractor = vtkRenderWindowInteractor()
    renderWindowInteractor.SetRenderWindow(renderWindow)

    # Enable user interface interactor.
    renderer.AddActor(actor)
    renderer.SetBackground(colors.GetColor3d('SteelBlue'))
    renderWindow.SetWindowName('CompositePolyDataMapper')
    renderWindow.Render()
    renderWindowInteractor.Start()


if __name__ == '__main__':
    main()
