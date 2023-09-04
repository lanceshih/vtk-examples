#!/usr/bin/env python3

import sys
from pathlib import Path

# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from lxml import etree
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersCore import vtkElevationFilter
from vtkmodules.vtkFiltersSources import vtkConeSource, vtkSphereSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer
)
from vtkmodules.vtkRenderingCore import (
    vtkDiscretizableColorTransferFunction,
)


def get_program_parameters(argv):
    import argparse
    description = 'Take an XML description of a colormap and convert it to a VTK colormap.'
    epilogue = '''
    A color transfer function in C++ or Python can be optionally generated.
    '''
    parser = argparse.ArgumentParser(description=description, epilog=epilogue,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('file_name', help='The path to the XML file e.g Fast.xml.')
    parser.add_argument('-d', action='store_true', dest='discretize', help='Discretize the colormap.')
    parser.add_argument('-n', dest='table_size', default=None, type=int,
                        help='Specify the size of the colormap.')
    parser.add_argument('-g', dest='generate_function', default=None,
                        help='Generate code for the color transfer function,'
                             ' specify the desired language one of: Cxx, Python.')

    args = parser.parse_args()
    return args.file_name, args.discretize, args.table_size, args.generate_function


def main(file_name, discretize, table_size, generate_function):
    if file_name:
        fn_path = Path(file_name)
        if not fn_path.suffix:
            fn_path = fn_path.with_suffix(".xml")
        if not fn_path.is_file():
            print('Unable to find: ', fn_path)
            return
    else:
        print('Please enter a path to the XML file.')
        return
    parameters = parse_xml(fn_path)
    # Do some checks.
    if len(parameters['data_values']) != len(parameters['color_values']):
        sys.exit('The data values length must be the same as colors.')
    if parameters['opacity_values'] is not None:
        if len(parameters['opacity_values']) != len(parameters['color_values']):
            sys.exit('The opacity values length must be the same as colors.')

    if generate_function is not None:
        generate_function = generate_function.lower()
        available_languages = {k.lower(): k for k in ['Cxx', 'Python']}
        available_languages.update({'cpp': 'Cxx', 'c++': 'Cxx'})
        if generate_function not in available_languages:
            print(f'The language: {generate_function} is not available.')
            tmp = ', '.join(sorted([lang for lang in set(available_languages.values())]))
            print(f'Choose one of these: {tmp}.')
            return
        else:
            language = available_languages[generate_function]
    else:
        language = None

    ctf = make_ctf(parameters, discretize, table_size)
    if language is not None and language in ['Cxx', 'Python']:
        if language == 'Python':
            generate_ctf_python(parameters, discretize, table_size)
        else:
            generate_ctf_cpp(parameters, discretize, table_size)

    colors = vtkNamedColors()
    colors.SetColor('ParaViewBkg', 82, 87, 110, 255)

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

    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(elevation_filter.GetOutputPort())
    mapper.SetLookupTable(ctf)
    mapper.SetColorModeToMapScalars()
    mapper.InterpolateScalarsBeforeMappingOn()

    actor = vtkActor()
    actor.SetMapper(mapper)
    # actor.GetProperty().SetDiffuseColor(colors.GetColor3d('bisque'))

    # Visualize
    ren = vtkRenderer()
    ren_win = vtkRenderWindow()
    ren_win.AddRenderer(ren)
    iren = vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)

    style = vtkInteractorStyleTrackballCamera()
    iren.SetInteractorStyle(style)

    ren.AddActor(actor)
    ren.SetBackground(colors.GetColor3d('ParaViewBkg'))

    ren_win.SetSize(640, 480)
    ren_win.SetWindowName('ColorMapToLUT_XML')

    ren_win.Render()
    iren.Start()


def parse_xml(fn_path):
    """
    Parse the XML file of a colormap.

    Check out: https://sciviscolor.org/colormaps/ for some good XML files.
    :param fn_path: The path to the XML file.
    :return: The parameters for the color map.
    """
    with open(fn_path) as data_file:
        xml_doc = etree.parse(data_file)
    data_values = list()
    color_values = list()
    opacity_values = list()
    nan = None
    above = None
    below = None

    s = xml_doc.getroot().find('ColorMap')
    if s is not None:
        color_map_details = dict(s.attrib)
    else:
        color_map_details = None
        sys.exit('The attribute "ColorMap" is not found.')
    for s in xml_doc.getroot().findall('.//Point'):
        data_values.append(s.attrib['x'])
        color_values.append((s.attrib['r'], s.attrib['g'], s.attrib['b']))
        opacity_values.append(s.attrib['o'])
    s = xml_doc.getroot().find('.//NaN')
    if s is not None:
        nan = (s.attrib['r'], s.attrib['g'], s.attrib['b'])
    s = xml_doc.getroot().find('.//Above')
    if s is not None:
        above = (s.attrib['r'], s.attrib['g'], s.attrib['b'])
    s = xml_doc.getroot().find('.//Below')
    if s is not None:
        below = (s.attrib['r'], s.attrib['g'], s.attrib['b'])
    return {'path': fn_path.name, 'color_map_details': color_map_details, 'data_values': data_values,
            'color_values': color_values, 'opacity_values': opacity_values, 'NaN': nan, 'Above': above, 'Below': below}


def make_ctf(parameters, discretize, table_size=None):
    """
    Generate the discretizable color transfer function
    :param parameters: The parameters.
    :param discretize: True if the values are to be mapped after discretization.
    :param table_size: The table size.
    :return: The discretizable color transfer function.
    """

    ctf = vtkDiscretizableColorTransferFunction()

    interp_space = parameters['color_map_details'].get('interpolationspace', None)
    if interp_space:
        interp_space = interp_space.lower()
        if interp_space == 'hsv':
            ctf.SetColorSpaceToHSV()
        elif interp_space == 'lab':
            ctf.SetColorSpaceToLab()
        elif interp_space == 'ciede2000':
            ctf.SetColorSpaceToLabCIEDE2000()
        elif interp_space == 'diverging':
            ctf.SetColorSpaceToDiverging()
        elif interp_space == 'step':
            ctf.SetColorSpaceToStep()
        else:
            ctf.SetColorSpaceToRGB()
    else:
        ctf.SetColorSpaceToRGB()

    scale = parameters['color_map_details'].get('interpolationtype', None)
    if scale:
        scale = scale.lower()
        if scale == 'log10':
            ctf.SetScaleToLog10()
        else:
            ctf.SetScaleToLinear()
    else:
        ctf.SetScaleToLinear()

    if parameters['NaN'] is not None:
        color = list(map(float, parameters['NaN']))
        ctf.SetNanColor(*color)

    if parameters['Above'] is not None:
        color = list(map(float, parameters['Above']))
        ctf.SetAboveRangeColor(*color)
        ctf.UseAboveRangeColorOn()

    if parameters['Below'] is not None:
        color = list(map(float, parameters['Below']))
        ctf.SetBelowRangeColor(*color)
        ctf.UseBelowRangeColorOn()

    space = parameters['color_map_details'].get('space', None)
    if space:
        space = space.lower()
        for i in range(0, len(parameters['data_values'])):
            color = list(map(float, parameters['color_values'][i]))
            idx = float(parameters['data_values'][i])
            if space == 'hsv':
                ctf.AddHSVPoint(idx, *color)
            else:
                ctf.AddRGBPoint(idx, *color)

    if table_size is not None:
        ctf.SetNumberOfValues(table_size)
    else:
        ctf.SetNumberOfValues(len(parameters["data_values"]))

    if discretize:
        ctf.DiscretizeOn()
    else:
        ctf.DiscretizeOff()

    return ctf


def generate_ctf_python(parameters, discretize, table_size=None):
    """
    Generate a function do the ctf.

    :param parameters: The parameters.
    :param discretize: True if the values are to be mapped after discretization.
    :param table_size: The table size.
    :return: The discretizable color transfer function.
    """
    indent = ' ' * 4

    comment = f'{indent}#'
    if 'name' in parameters['color_map_details']:
        comment += f' name: {parameters["color_map_details"]["name"]},'
    if 'creator' in parameters['color_map_details']:
        comment += f' creator: {parameters["color_map_details"]["creator"]},'
    comment += f' file name: {parameters["path"]}'

    s = ['', f'def get_ctf():', comment, f'{indent}ctf = vtkDiscretizableColorTransferFunction()', '']

    interp_space = parameters['color_map_details'].get('interpolationspace', None)
    if interp_space:
        interp_space = interp_space.lower()
        if interp_space == 'hsv':
            s.append(f'{indent}ctf.SetColorSpaceToHSV()')
        elif interp_space == 'lab':
            s.append(f'{indent}ctf.SetColorSpaceToLab()')
        elif interp_space == 'ciede2000':
            s.append(f'{indent}ctf.SetColorSpaceToLabCIEDE2000()')
        elif interp_space == 'diverging':
            s.append(f'{indent}ctf.SetColorSpaceToDiverging()')
        elif interp_space == 'step':
            s.append(f'{indent}ctf.SetColorSpaceToStep()')
        else:
            s.append(f'{indent}ctf.SetColorSpaceToRGB()')
    else:
        s.append(f'{indent}ctf.SetColorSpaceToRGB()')

    scale = parameters['color_map_details'].get('interpolationtype', None)
    if scale:
        scale = scale.lower()
        if scale == 'log10':
            s.append(f'{indent}ctf.SetScaleToLog10()')
        else:
            s.append(f'{indent}ctf.SetScaleToLinear()')
    else:
        s.append(f'{indent}ctf.SetScaleToLinear()')
    s.append('')

    if parameters['NaN'] is not None:
        color = ', '.join(parameters['NaN'])
        s.append(f'{indent}ctf.SetNanColor({color})')

    if parameters['Above'] is not None:
        color = ', '.join(parameters['Above'])
        s.append(f'{indent}ctf.SetAboveRangeColor({color})')
        s.append(f'{indent}ctf.UseAboveRangeColorOn()')

    if parameters['Below'] is not None:
        color = ', '.join(parameters['Below'])
        s.append(f'{indent}ctf.SetBelowRangeColor({color})')
        s.append(f'{indent}ctf.UseBelowRangeColorOn()')
    s.append('')

    space = parameters['color_map_details'].get('space', None)
    if space:
        space = space.lower()
        for i in range(0, len(parameters['data_values'])):
            color = ', '.join(parameters['color_values'][i])
            idx = parameters['data_values'][i]
            if space == 'hsv':
                s.append(f'{indent}ctf.AddHSVPoint({idx}, {color})')
            else:
                s.append(f'{indent}ctf.AddRGBPoint({idx}, {color})')
        s.append('')

    if table_size is not None:
        s.append(f'{indent}ctf.SetNumberOfValues({table_size})')
    else:
        s.append(f'{indent}ctf.SetNumberOfValues({len(parameters["data_values"])})')

    if discretize:
        s.append(f'{indent}ctf.DiscretizeOn()')
    else:
        s.append(f'{indent}ctf.DiscretizeOff()')
    s.append('')

    s.append(f'{indent}return ctf')
    s.append('')

    print('\n'.join(s))


def generate_ctf_cpp(parameters, discretize, table_size=None):
    """
    Generate a function do the ctf.

    :param parameters: The parameters.
    :param discretize: True if the values are to be mapped after discretization.
    :param table_size: The table size.
    :return: The discretizable color transfer function.
    """
    indent = ' ' * 2

    comment = f'{indent}//'
    if 'name' in parameters['color_map_details']:
        comment += f' name: {parameters["color_map_details"]["name"]},'
    if 'creator' in parameters['color_map_details']:
        comment += f' creator: {parameters["color_map_details"]["creator"]},'
    comment += f' file name: {parameters["path"]}'

    s = ['', f'vtkNew<vtkDiscretizableColorTransferFunction> getCTF()', '{', comment,
         f'{indent}vtkNew<vtkDiscretizableColorTransferFunction> ctf;', '']

    interp_space = parameters['color_map_details'].get('interpolationspace', None)
    if interp_space:
        interp_space = interp_space.lower()
        if interp_space == 'hsv':
            s.append(f'{indent}ctf->SetColorSpaceToHSV();')
        elif interp_space == 'lab':
            s.append(f'{indent}ctf->SetColorSpaceToLab();')
        elif interp_space == 'ciede2000':
            s.append(f'{indent}ctf->SetColorSpaceToLabCIEDE2000();')
        elif interp_space == 'diverging':
            s.append(f'{indent}ctf->SetColorSpaceToDiverging();')
        elif interp_space == 'step':
            s.append(f'{indent}ctf->SetColorSpaceToStep();')
        else:
            s.append(f'{indent}ctf->SetColorSpaceToRGB();')
    else:
        s.append(f'{indent}ctf->SetColorSpaceToRGB();')

    scale = parameters['color_map_details'].get('interpolationtype', None)
    if scale:
        scale = scale.lower()
        if scale == 'log10':
            s.append(f'{indent}ctf->SetScaleToLog10();')
        else:
            s.append(f'{indent}ctf->SetScaleToLinear();')
    else:
        s.append(f'{indent}ctf->SetScaleToLinear();')
    s.append('')

    if parameters['NaN'] is not None:
        color = ', '.join(parameters['NaN'])
        s.append(f'{indent}ctf->SetNanColor({color});')

    if parameters['Above'] is not None:
        color = ', '.join(parameters['Above'])
        s.append(f'{indent}ctf->SetAboveRangeColor({color});')
        s.append(f'{indent}ctf->UseAboveRangeColorOn();')

    if parameters['Below'] is not None:
        color = ', '.join(parameters['Below'])
        s.append(f'{indent}ctf->SetBelowRangeColor({color});')
        s.append(f'{indent}ctf->UseBelowRangeColorOn();')
    s.append('')

    space = parameters['color_map_details'].get('space', None)
    if space:
        space = space.lower()
        for i in range(0, len(parameters['data_values'])):
            color = ', '.join(parameters['color_values'][i])
            idx = parameters['data_values'][i]
            if space == 'hsv':
                s.append(f'{indent}ctf->AddHSVPoint({idx}, {color});')
            else:
                s.append(f'{indent}ctf->AddRGBPoint({idx}, {color});')
        s.append('')

    if table_size is not None:
        s.append(f'{indent}ctf->SetNumberOfValues({table_size});')
    else:
        s.append(f'{indent}ctf->SetNumberOfValues({len(parameters["data_values"])});')

    if discretize:
        s.append(f'{indent}ctf->DiscretizeOn();')
    else:
        s.append(f'{indent}ctf->DiscretizeOff();')
    s.append('')

    s.append(f'{indent}return ctf;')
    s.append('}')
    s.append('')

    print('\n'.join(s))


if __name__ == '__main__':
    file, discretise, size, generate = get_program_parameters(sys.argv)
    main(file, discretise, size, generate)
