#!/usr/bin/env python3


import numpy as np
import pandas as pd
import math, re, os, time


pathin = input("\nPlease Enter the Directory Contained Your File:\n")
inputf = input("\nPlease Enter the SCAN Result File: (*.log)\n")
method = input("\nThe Computational Method:\n")
angID1 = input("\nPlease Enter the indices of the 1st dihedral angle (e.g. 1,2,3,4):\n")
angID2 = input("\nPlease Enter the indices of the 2nd dihedral angle (e.g. 2,3,4,5):\n")


def extract_elements(fo):
    elements = []
    for line in fo:
        temp = line.strip().split()
        if not line.startswith("    ") and len(temp) > 0:
            elements.append(temp[0][0])
        else:
            break
    #print(elements)
    return elements, len(elements)


def parse_info(fo, pattern_orient, len_elements, pattern_energy, pattern_statny):
    ''' parse the information from the Gaussian09 scan result (*.log file),
    line by line.
    Return the coordinates and the energy at the stationary point.
    '''
    coords = np.chararray((len_elements, 3), itemsize=14)
    while fo:
        line = next(fo)
        if re.search(pattern_orient, line):
            xyzlist = []
            for i in range(4):
                line = next(fo)
            for i in range(len_elements):
                line = next(fo)
                xyz = line.strip().split()[3:6]
                xyzlist.append(xyz)
            coords[:] = xyzlist
            #print("\ncoordinates:\n{:}\n".format(coords))
            
        if line.startswith(' SCF Done:'):
            energy = []
            match_energy = re.search(pattern_energy, line)
            if match_energy:
                energy.append(match_energy.group(1))
            #print("\nenergy:\n{:}\n".format(energy))
        elif re.search(pattern_statny, line):
            break
        
    if energy and coords.size > 0:
        return energy[-1], coords
    return energy, coords # empty list


def calc_dihedral_angles(coordinates):
    ''' Using the Gram–Schmidt process to calculate the dihedral_angle
    of atom1-atom2-atom3-atom4 (e.g. N--C_alpha--C--O) in each residue
    of the protine (PDB file).
        This function returns a 1D data array of the dihedral angles
    in the unit of degree.
    '''
    p1 = np.asfarray(coordinates[0,:], dtype=np.float64)
    p2 = np.asfarray(coordinates[1,:], dtype=np.float64)
    p3 = np.asfarray(coordinates[2,:], dtype=np.float64)
    p4 = np.asfarray(coordinates[3,:], dtype=np.float64)
    
    b0 = -1.0 * (p2 - p1)
    b1 = p3 - p2
    b2 = p4 - p3
    
    # normalize b1 so that it does not influence magnitude of vector
    # projections that come next
    b1 /= np.linalg.norm(b1)
    
    # vector projection using Gram–Schmidt process
    # v = projection of b0 onto plane perpendicular to b1
    #   = b0 minus component that aligns with b1
    # w = projection of b2 onto plane perpendicular to b1
    #   = b2 minus component that aligns with b1
    v = b0 - np.dot(b0, b1) * b1
    w = b2 - np.dot(b2, b1) * b1
    
    # angle between v and w in a plane is the torsion angle
    # v and w may not be normalized but that's fine since tan is y/x
    x = np.dot(v, w)
    y = np.dot(np.cross(b1, v), w)
    return np.rad2deg(np.arctan2(y, x))


def save_structure_xyz(path, inputf, elements, coords, method, model_num):
    ''' Save the stucture into a file in the .xyz format.
    '''
    output_fname = ''.join((os.path.splitext(inputf)[0], '_', method, '.xyz'))
    path_outfile = os.path.join(path, output_fname)
    fmt_commentline = "Model_number = {:}\n"
    fmt_coordinates = "%-14s %+14s %+14s %+14s"
    geom = np.column_stack((elements, coords))
    
    with open(path_outfile, 'a') as fw:
        fw.write(''.join((str(len(elements)),'\n')))
        fw.write(fmt_commentline.format(model_num))
        np.savetxt(fw, geom, fmt=fmt_coordinates)
    print("Save the coordinates.".format(model_num))


def main(path, filename, method, angID1, angID2):
    ''' Work Flow:
    read file line by line;
    extract the energy at each stationary point;
    extract the optimized geometry step by step.
    '''
    initial_time = time.time()

    phi_ids = np.array(angID1.split(',' or ' '), dtype=int) - 1
    psi_ids = np.array(angID2.split(',' or ' '), dtype=int) - 1
    
    energy_list = []
    phi_list = []
    psi_list = []

    str_checkpoint = r"\s+Charge\s+=\s+\d+\s+Multiplicity\s+=\s+\d+"
    str_energy_val = r"\s+E\(.*\)\s+=\s+([-+]?\d*\.\d+)"
    str_stationary = r"\s+Stationary point found.\s+"
    str_std_orient = r"\s+Standard orientation:\s+"

    pattern_checks = re.compile(str_checkpoint)
    pattern_energy = re.compile(str_energy_val)
    pattern_statny = re.compile(str_stationary)
    pattern_orient = re.compile(str_std_orient)

    terminations = (' Error termination', ' Normal termination')
    initial_time = time.time()
    
    with open(os.path.join(path, filename), 'r') as fo:

        model_num = 1
        
        #### skip lines until hit the structure information.
        for line in fo:
            if re.search(pattern_checks, line):
                break
        
        #### extract the elements information
        elements, len_elements = extract_elements(fo)
        
        #### extract stationary energy, structure, calculate Phis, Psi,
        #### combining them with energy in the loop, 
        #### and save the results in each loop.
        
        print_line = ''.join(('\n', '-' * 50, '\n'))
        print_fmt = ''.join((print_line, "Model Number: {:>6d}"))
        step_fmt = "Step {:} Complete! Used Time: {:.3f} Seconds."
        for line in fo:
            try:
                if line.startswith(terminations):
                    break
                else:
                    #### extract enery & coordinates at each stationary point.
                    start_time = time.time()
                    energy, coords = parse_info(fo, pattern_orient,
                                                len_elements,
                                                pattern_energy,
                                                pattern_statny)
                    if energy and coords.size > 0:
                        print(print_fmt.format(model_num))
                        #save_structure_xyz(path, inputf, elements,
                        #                   coords, method, model_num)
                        print(step_fmt.format(model_num,
                                              time.time() - start_time))
                        energy_list.append(energy)
                        phi = calc_dihedral_angles(coords[phi_ids])
                        psi = calc_dihedral_angles(coords[psi_ids])
                        phi_list.append(phi)
                        psi_list.append(psi)
                    
                    model_num += 1
            except StopIteration:
                break
            
        Phi = np.array(phi_list, dtype=np.float64)
        Psi = np.array(psi_list, dtype=np.float64)
        Eng = np.array(energy_list, dtype=np.float64) * 627.5095
                
        title = ['Phi', 'Psi', 'Energy (kcal/mol)']
        df = pd.DataFrame(np.column_stack((Phi, Psi, Eng)), columns=title)
                
        output = ''.join(('Model_', inputf[:4], '.csv'))
        df.to_csv(os.path.join(pathin, output), sep=',',
                  columns=title, index=False)
        
        fmt = "\nWork Complete! Used Time: {:.3f} Seconds."
        print(fmt.format(time.time() - initial_time))                        
                    

if __name__ == "__main__":
    main(pathin, inputf, method, angID1, angID2)
