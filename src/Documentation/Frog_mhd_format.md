# Frog MHD Format

The following keys are recognised:

## Keys

- **title**: A title.
- **files**: A vector/list of paths to the *.mhd files needed.
- **tissues**
  - **colors**: A map/dict of tissue names and colors.
- **figures**
  - **fig12-9b**: The vector/list of tissues needed for figure 12-9b.
  - **fig12-9cd**: The vector/list of tissues needed for figure 12-9c and 12-9d.
- **tissue_parameters**: The required parameters for each tissue are specified here.
  - **parameter types**: A map/dict of tissue parameters of each tissue parameter and its type. Essential for C++ code.
  - **default**>: The default tissue parameters, a map/dict of tissue parameters and values.
  - <**tissue name**>: The map/dict of tissue parameters and values for each tissue.
