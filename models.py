
import numpy as np

import re 
import glob
import pyfits

import interpol

defaults = None

def get_files(evolution_model):
   """
   Returns list of files belonging to the requested evolution models together
   with a list of the metalicity of each file
   
   curently recognized models are: 
    - mist_vvcrit0.0
   """
   
   if evolution_model == 'mist_vvcrit0.0' or evolution_model == 'mist':
      files = glob.glob('MIST/MIST_v1.0_feh_*_afe_p0.0_vvcrit0.0_basic.fits')
   
   elif evolution_model == 'mist_vvcrit0.4':
      files = glob.glob('MIST/MIST_v1.0_feh_*_afe_p0.0_vvcrit0.4_basic.fits')
   
   else:
      # default to MIST if models not recognized
      files = glob.glob('MIST/MIST_v1.0_feh_*_afe_p0.0_vvcrit0.0_basic.fits')
   
   files = sorted(files)
   
   # exctract metalicity from name
   z = np.zeros_like(files, dtype=float)
   for i, f in enumerate(files):
      sign, z_ = re.findall('([mp])(\d\.\d\d)', f)[0]
      z[i] = float(z_) * -1 if sign == 'm' else float(z_)
   
   return files, z

def prepare_grid(evolution_model='mist_vvcrit0.0',
                 parameters=['initial_mass', 'log10_age_yr', 'feh'], 
                 variables=['log_L', 'log_Teff', 'log_g', 'feh'],
                 set_default=False, 
                 **kwargs):
   """
   Prepares the stellar evolution models by creating a pixelgrid to be used in interpolate
   This method will read the stellar evolution models from file, select only 
   the columns you want to interpolate over (given in parameter_names), and will 
   return axis_values, pixelgrid to be used in interpolate. 
   
   You can also provide limits on the size of the grid in mass, feh and age by
   setting the mass_lim, feh_lim and age_lim keywords
   
   """
   
   files, fehs = get_files(evolution_model)
   
   grid_pars = []
   grid_vars = []
   
   fehlim = kwargs.pop('feh_lim', (-np.inf, np.inf))
   
   for filename, z in zip(files, fehs):
      
      #-- skip the file if it is out of metalicity range
      if z < fehlim[0] or z > fehlim[1]: continue
      
      data = pyfits.getdata(filename)
      
      keep = np.ones(len(data),bool)
      
      #-- run over all provided kwargs to check if any limitations on the grid
      #   are requested, and apply them. Limits can be given for any parameter
      #   in the grid.
      for key in kwargs:
         if not '_lim' in key: continue
         
         low, high = kwargs[key][0], kwargs[key][1]
         key = key.replace('_lim', '')
         in_range = (low<=data[key]) & (data[key]<=high)
      
         keep = keep & in_range
      data = data[keep]
      
      #-- only keep the parameters and variables that are needed to reduce memory
      pars_ = np.vstack([data[name] for name in parameters])
      vars_ = np.vstack([data[name] for name in variables])
      
      if sum(keep):
         grid_pars.append(pars_)
         grid_vars.append(vars_)
   
   grid_pars = np.hstack(grid_pars)
   grid_vars = np.hstack(grid_vars)
   
   axis_values, pixelgrid = interpol.create_pixeltypegrid(grid_pars, grid_vars)
   
   if set_default:
      #-- store the prepared pixel grid to be used by interpolation functions
      global defaults
      defaults = (axis_values, pixelgrid)
   
   return axis_values, pixelgrid
         

def interpolate(mass, age, feh, **kwargs):
   """
   Returns the requested values from the stellar evolution grids at the given 
   values for the input parameters (mass, feh, age)
   """
   
   global defaults
   if 'grid' in kwargs:
      axis_values, pixelgrid = kwargs['grid']
   elif not defaults is None:
      axis_values, pixelgrid = defaults
   else:
      axis_values, pixelgrid = prepare_grid()
   
   multiple = False
   if not hasattr(mass, '__iter__') or not hasattr(age, '__iter__') or \
      not hasattr(feh, '__iter__'):
      mass = np.array(mass)
      age = np.array(age)
      feh = np.array(feh)
      multiple = True
   
   p = np.vstack([mass, age, feh])
   
   values = interpol.interpolate(p, axis_values, pixelgrid)
   
   if multiple:
      values = values.flatten()
      
   return values

def get_isochrone(age, feh, **kwargs):
   """
   returns an isochrone for the requested metalicity and age
   The mass points of the track are the gridpoints included in the evolution grid
   """
   
   mass = sorted(set(axis_values[0]))
   
   age = np.ones_like(mass) * age
   feh = np.ones_like(mass) * feh
   
   return interpolate(mass, age, feh, **kwargs)

def get_track(mass, feh, **kwargs):
   """
   Returns an evolution track for a given mass and metalicity. 
   The age points of the track are the gridpoints included in the evolution grid
   """
   
   age = sorted(set(axis_values[1]))
   
   mass = np.ones_like(age) * mass
   feh = np.ones_like(age) * feh
   
   return interpolate(mass, age, feh, **kwargs)

if __name__=="__main__":

 axis_values, pixelgrid = prepare_grid(parameters=['initial_mass', 'log10_age_yr', 'feh'], 
                         variables=['log_L', 'log_Teff', 'log_g', 'feh'],
                         log10_age_yr_lim=(5.0, 9.0),
                         initial_mass_lim = (0.4, 2.6), 
                         feh_lim = (-1.0, 0.5),
                          )