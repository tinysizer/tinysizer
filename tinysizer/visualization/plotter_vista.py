import pyvista as pv
import numpy as np
import pandas as pd
from matplotlib import cm
from PySide6.QtWidgets import QFrame, QVBoxLayout
from pyvistaqt import QtInteractor

class PyVistaMeshPlotter(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create layout that fills the entire frame
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create PyVista plotter with Qt interactor
        # Setting interactive=True enables mouse interaction
        self.plotter = QtInteractor(self, auto_update=True)
        layout.addWidget(self.plotter)
        
        # Set background color
        self.plotter.set_background([0.2, 0.2, 0.3])  # Dark blue-gray
        
        # Add axes for reference
        self.add_axes()
        self.element_to_cell_map = {}
        self.model_data=None
        
        # Set flag for tracking if we've rendered anything
        self.has_rendered = False
        self.mesh=None
        self.mesh_sizing=None

    def add_axes(self):
        """Add coordinate axes to scene"""
        self.plotter.add_axes(xlabel='X', ylabel='Y', zlabel='Z', 
                              line_width=2, labels_off=False)

    #SIZING TABDA PROP CİZER
    #redundant olabilir alttaki plot_mesh'den bazi yerleri kullanip kısaltilabilir mi ? -ymn
    def plot_sizing_tab(self,model_data,pid): 
        pid2eid=model_data.bdf.get_property_id_to_element_ids_map()
        nodes,elements=[],[]
        
        try:
            elids=pid2eid[pid]
        except:
            print(f"Invalid property id {pid}")
            self.plotter.clear()
            self.add_axes()
            self.plotter.add_text("Invalid property", position='lower_right', font_size=8, color='gray')
            return
        
        elements.extend(elids)
        for elid in elids:
            nodes.extend(model_data.bdf.elements[elid].nodes)

        # Clear existing actors
        self.plotter.clear()
        self.add_axes()

        ####################################################################
        ########## DOING POINTS !!! -> later pv.PolyData(points,faces)
        ####################################################################
        points = []
        node_id_to_idx = {} #-> {101:1, 102:2, 103:3 .... node_id : index}
        idx = 0
        cell_idx=0

        # Process nodes
        for nid in nodes:
            try:
                coords=model_data.bdf.nodes[nid].get_position()  
                points.append(coords)
                
                # Store the mapping from node ID to point index
                node_id_to_idx[nid] = idx
                idx += 1
                
            except Exception as e:
                print(f"Error processing node {nid}: {str(e)}")
        
        points = np.array(points)
        print(f"Successfully processed {len(points)} nodes")
        

        ####################################################################
        ########## DOING FACES !!! -> later pv.PolyData(points,faces)
        ####################################################################
        quad_faces = []
        tri_faces = []
        bar_lines = []
        
        # Process quad elements (CQUAD4)
        for eid in elements:
            node_ids=model_data.bdf.elements[eid].nodes
            if model_data.bdf.elements[eid].type=="CQUAD4":
                # PyVista expects faces as [n, id1, id2, ..., idn] where n is the number of points
                face_indices = []
                valid_element = True
                    
                for nid in node_ids:
                    if nid in node_id_to_idx:
                        face_indices.append(node_id_to_idx[nid])
                    else:
                        print(f"Node {nid} from element {eid} not found in node map")
                        valid_element = False
                        break
                
                if valid_element:
                    # Format for PyVista: [4, idx0, idx1, idx2, idx3]
                    quad_faces.append([4] + face_indices)
                    #self.element_to_cell_map[eid] = cell_idx
                    cell_idx += 1

        # Process triangular elements (CTRIA3)
            elif model_data.bdf.elements[eid].type=="CTRIA3":
                face_indices = []
                valid_element = True
                
                for nid in node_ids:
                    if nid in node_id_to_idx:
                        face_indices.append(node_id_to_idx[nid])
                    else:
                        print(f"Node {nid} from element {eid} not found in node map")
                        valid_element = False
                        break
                
                if valid_element:
                    # Format for PyVista: [3, idx0, idx1, idx2]
                    tri_faces.append([3] + face_indices)
                    cell_idx += 1

        # Process bar elements (CBAR) -> asagida da benzer yer var, redundant olabilir mi burasi ? -ymn
            elif model_data.bdf.elements[eid].type=="CBAR":
                line_indices = []
                valid_element = True
                
                for nid in node_ids:
                    if nid in node_id_to_idx:
                        line_indices.append(node_id_to_idx[nid])
                    else:
                        print(f"Node {nid} from element {eid} not found in node map")
                        valid_element = False
                        break
                
                if valid_element:
                    # Format for PyVista: [2, idx0, idx1]
                    bar_lines.append([2] + line_indices)
                    cell_idx += 1

        print(f"Successfully processed {len(quad_faces)} quads & {len(tri_faces)} triangles & {len(bar_lines)} bars.")


        ####################################################################
        ########## PLOTTING !!! -> pv.PolyData(points,faces)
        ####################################################################
        self.mesh_sizing=pv.PolyData()
        # Combine all faces for a single mesh
        faces = quad_faces + tri_faces
        if faces:
            # Convert to the format PyVista expects
            faces_array = []
            for face in faces:
                faces_array.extend(face)
            
            # Create the mesh
            surface_mesh = pv.PolyData(points, faces=faces_array)
            self.mesh_sizing = self.mesh_sizing.merge(surface_mesh) #later for colorizng by property -ymn

            
            self.plotter.add_mesh(surface_mesh, show_edges=True, color=[0.8, 0.8, 0.8], 
                                edge_color='black', line_width=1.5, opacity=1.0)
            
            print(f"Created mesh with {surface_mesh.n_points} points and {surface_mesh.n_cells} cells")


        if bar_lines:
            flat_lines = [i for line in bar_lines for i in line]
            line_mesh = pv.PolyData()
            line_mesh.points = points
            line_mesh.lines = flat_lines
            self.mesh_sizing = self.mesh_sizing.merge(line_mesh) #later for colorizng by property -ymn
			
            self.plotter.add_mesh(line_mesh, show_edges=True, color=[0.8, 0.8, 0.8], 
                                                edge_color='black', line_width=1.5, opacity=1.0)
                                                
        text=f"{model_data.bdf.properties[pid].type} {pid}"
        self.plotter.add_text(text, position='lower_right', font_size=8, color='gray')
        self.plotter.reset_camera()
        self.plotter.update()
        #self.has_rendered = True
        print("Rendering complete")


    def plot_mesh(self, model_data, result_type=None, subcase_id=None, component=None):
        """
        Plot mesh from ModelData with optional results visualization
        
        Parameters:
        -----------
        model_data : ModelData
            The loaded model data object
        result_type : str, optional
            Type of result to visualize (e.g., 'DISPLACEMENT', 'STRESS')
        subcase_id : int, optional
            Subcase ID to visualize
        component : str, optional
            Specific component to visualize (e.g., 'von_mises', 'T1', 'T2', 'T3')
        """
        
        # Extract nodes and elements from model_data
        nodes = model_data.nodes
        elements = model_data.elements
        print(model_data)
        self.model_data=model_data
        
        print("Plot mesh called with:", len(nodes) if nodes else 0, "nodes and", 
            len(elements.get('CQUAD4', [])) + len(elements.get('CTRIA3', [])), "elements")
        
        if not nodes:
            print("No nodes provided")
            return
            
        # Clear existing actors
        self.plotter.clear()
        self.add_axes()
        

        ####################################################################
        ########## DOING POINTS !!! -> later pv.PolyData(points,faces)
        ####################################################################
        points = []
        node_id_to_idx = {} #-> {101:1, 102:2, 103:3 .... node_id : index}
        idx = 0
        cell_idx=0

        # Process nodes
        for nid, grid_obj in nodes.items():
            try:
                # Extract coordinates from pyNastran GRID objects
                if hasattr(grid_obj, 'xyz'):
                    coords = grid_obj.xyz
                elif hasattr(grid_obj, 'get_position'):
                    coords = grid_obj.get_position()
                else:
                    print(f"Skipping node {nid} - no coordinate data found")
                    continue
                    
                # Add the point
                points.append(coords)
                
                # Store the mapping from node ID to point index
                node_id_to_idx[nid] = idx
                idx += 1
                
            except Exception as e:
                print(f"Error processing node {nid}: {str(e)}")
        
        points = np.array(points)
        print(f"Successfully processed {len(points)} nodes")
        

        ####################################################################
        ########## DOING FACES !!! -> later pv.PolyData(points,faces)
        ####################################################################
        quad_faces = []
        tri_faces = []
        bar_lines = []
        
        # Process quad elements (CQUAD4)
        for elem_data in elements.get('CQUAD4', []):
            try:
                # Our enhanced structure uses tuples: (typ, pid, eid, node_ids)
                if isinstance(elem_data, tuple) and len(elem_data) >= 4:
                    _, _, eid, node_ids = elem_data
                else:
                    print(f"Unsupported quad element format: {type(elem_data)}")
                    continue
                
                # PyVista expects faces as [n, id1, id2, ..., idn] where n is the number of points
                face_indices = []
                valid_element = True
                
                for nid in node_ids:
                    if nid in node_id_to_idx:
                        face_indices.append(node_id_to_idx[nid])
                    else:
                        print(f"Node {nid} from element {eid} not found in node map")
                        valid_element = False
                        break
                
                if valid_element:
                    # Format for PyVista: [4, idx0, idx1, idx2, idx3]
                    quad_faces.append([4] + face_indices)
                    cell_idx += 1

            except Exception as e:
                print(f"Error processing quad element: {str(e)}")
        
        # Process triangular elements (CTRIA3)
        for elem_data in elements.get('CTRIA3', []):
            try:
                # Our enhanced structure uses tuples: (typ, pid, eid, node_ids)
                if isinstance(elem_data, tuple) and len(elem_data) >= 4:
                    _, _, eid, node_ids = elem_data
                else:
                    print(f"Unsupported triangle element format: {type(elem_data)}")
                    continue
                
                face_indices = []
                valid_element = True
                
                for nid in node_ids:
                    if nid in node_id_to_idx:
                        face_indices.append(node_id_to_idx[nid])
                    else:
                        print(f"Node {nid} from element {eid} not found in node map")
                        valid_element = False
                        break
                
                if valid_element:
                    # Format for PyVista: [3, idx0, idx1, idx2]
                    tri_faces.append([3] + face_indices)
                    cell_idx += 1

            except Exception as e:
                print(f"Error processing triangle element: {str(e)}")
        

        # Process bar elements (CBAR) -> asagida da benzer yer var, redundant olabilir mi burasi ? -ymn
        for elem_data in elements.get('CBAR', []):
            try:
                # Our enhanced structure uses tuples: (typ, pid, eid, node_ids)
                if isinstance(elem_data, tuple) and len(elem_data) >= 4:
                    _, _, eid, node_ids = elem_data
                else:
                    continue
                
                line_indices = []
                valid_element = True
                
                for nid in node_ids:
                    if nid in node_id_to_idx:
                        line_indices.append(node_id_to_idx[nid])
                    else:
                        print(f"Node {nid} from element {eid} not found in node map")
                        valid_element = False
                        break
                
                if valid_element:
                    # Format for PyVista: [2, idx0, idx1]
                    bar_lines.append([2] + line_indices)
                    cell_idx += 1

            except Exception as e:
                print(f"Error processing triangle element: {str(e)}")


        print(f"Successfully processed {len(quad_faces)} quads & {len(tri_faces)} triangles & {len(bar_lines)} bars.")


        ####################################################################
        ########## PLOTTING !!! -> pv.PolyData(points,faces)
        ####################################################################
        self.mesh=pv.PolyData()
        if quad_faces or tri_faces:
            # Combine all faces for a single mesh
            faces = quad_faces + tri_faces
            if faces:
                # Convert to the format PyVista expects
                faces_array = []
                for face in faces:
                    faces_array.extend(face)
                
                # Create the mesh
                surface_mesh = pv.PolyData(points, faces=faces_array)
                self.mesh = self.mesh.merge(surface_mesh) #later for colorizng by property -ymn

                # Process and add results if requested
                if (result_type and subcase_id and 
                    result_type in model_data.results and 
                    subcase_id in model_data.get_available_subcases(result_type)):
                    
                    # Get result data using our enhanced function
                    result_data = model_data.get_result_data(result_type, subcase_id, component)

                    if result_data and "bar" not in result_type.lower(): #bar sonuclarini almiyorum, varsa asagida else ile gri oluyor -ymn

                        # Get the appropriate label for the scalars
                        scalar_label = component if component else result_type.lower()

                        if result_type == 'DISPLACEMENT':
                            # Displacement is a nodal result
                            node_values = np.zeros(len(points))
                            
                            for nid, value in result_data.items():
                                if nid in node_id_to_idx:
                                    idx = node_id_to_idx[nid]
                                    node_values[idx] = value
                                
                            # Add as point data
                            surface_mesh.point_data[scalar_label] = node_values
                            
                            # Add the mesh with the results
                            self.plotter.add_mesh(surface_mesh, scalars=scalar_label, show_edges=True,
                                                cmap='jet', edge_color='black', line_width=1.5,
                                                scalar_bar_args={"title": f"{result_type} ({scalar_label})"})


                        else:
                            # Element results require a bit more work
                            # We need to map element ids to cell ids in the mesh
                            element_values = np.zeros(len(faces))
                            
                            # Create mapping from element ID to cell index
                            cell_to_element_map = {}
                            cell_idx = 0
                            
                            # Map quad elements
                            for elem_data in elements.get('CQUAD4', []):
                                if isinstance(elem_data, tuple) and len(elem_data) >= 4:
                                    _, _, eid, _ = elem_data
                                elif hasattr(elem_data, 'eid'):
                                    eid = elem_data.eid
                                else:
                                    continue
                                    
                                cell_to_element_map[cell_idx] = eid
                                cell_idx += 1
                            
                            # Map tri elements
                            for elem_data in elements.get('CTRIA3', []):
                                if isinstance(elem_data, tuple) and len(elem_data) >= 4:
                                    _, _, eid, _ = elem_data
                                elif hasattr(elem_data, 'eid'):
                                    eid = elem_data.eid
                                else:
                                    continue
                                    
                                cell_to_element_map[cell_idx] = eid
                                cell_idx += 1


                            # Assign result values to cells
                            for cell_idx, eid in cell_to_element_map.items():
                                if eid in result_data and cell_idx < len(element_values):
                                    element_values[cell_idx] = result_data[eid]
                            
                            # Add as cell data
                            surface_mesh.cell_data[scalar_label] = element_values
                            
                            # Add the mesh with the results
                            self.plotter.add_mesh(surface_mesh, scalars=scalar_label, show_edges=True,
                                                cmap='jet', edge_color='black', line_width=1.5,
                                                scalar_bar_args={"title": f"{result_type} ({scalar_label})"})
        
                    else:
                        # No result data, add mesh with default appearance
                        self.plotter.add_mesh(surface_mesh, show_edges=True, color=[0.8, 0.8, 0.8], 
                                            edge_color='black', line_width=1.5, opacity=1.0)
                else:
                    # No results specified, add mesh with default appearance
                    self.plotter.add_mesh(surface_mesh, show_edges=True, color=[0.8, 0.8, 0.8],
                                        edge_color='black', line_width=1.5, opacity=1.0)
                
                print(f"Created mesh with {surface_mesh.n_points} points and {surface_mesh.n_cells} cells")
        
        
        # Plot CBAR lines
        if bar_lines:
            flat_lines = [i for line in bar_lines for i in line]
            line_mesh = pv.PolyData()
            line_mesh.points = points
            line_mesh.lines = flat_lines
            self.mesh = self.mesh.merge(line_mesh) #later for colorizng by property -ymn

            if (result_type and subcase_id and 
                    result_type in model_data.results and 
                    subcase_id in model_data.get_available_subcases(result_type)
                    and "bar" in result_type.lower()): #bar sonuclarini aliyorum, result_data tekrar cekmek gerekiyor yukarida girmedi cünkü -ymn

                    # Get result data using our enhanced function
                    result_data = model_data.get_result_data(result_type, subcase_id, component)

                    # Get the appropriate label for the scalars
                    scalar_label = component if component else result_type.lower()

                    bar_values = np.zeros(len(bar_lines))
                    bar_cell_map = {}
                    for i, elem_data in enumerate(elements.get('CBAR', [])):
                        if isinstance(elem_data, tuple) and len(elem_data) >= 4:
                            _, _, eid, _ = elem_data
                        elif hasattr(elem_data, 'eid'):
                            eid = elem_data.eid
                        else:
                            continue
                        bar_cell_map[i] = eid

                    for cell_idx, eid in bar_cell_map.items():
                        if eid in result_data and cell_idx < len(bar_values):
                            bar_values[cell_idx] = result_data[eid]

                    line_mesh.cell_data[scalar_label] = bar_values
                                        
                    self.plotter.add_mesh(line_mesh, scalars=scalar_label, show_edges=True,
                                        cmap='jet', edge_color='black', line_width=2.5,
                                        scalar_bar_args={"title": f"{result_type} ({scalar_label})"})
     
            else:
                # No results specified, add mesh with default appearance
                self.plotter.add_mesh(line_mesh, show_edges=True, color=[0.8, 0.8, 0.8], 
                                    edge_color='black', line_width=1.5, opacity=1.0)


        if not quad_faces and not tri_faces and not bar_lines:
            point_cloud = pv.PolyData(points)
            self.plotter.add_mesh(point_cloud, render_points_as_spheres=True,
                                point_size=10, color='red')
            print("No elements found, displaying points only")

        self.create_element_mapping_after_merge()
        self.plotter.reset_camera()
        self.plotter.update()
        self.has_rendered = True

        print("Rendering complete")


    def create_element_mapping_after_merge(self):
        """Build mapping AFTER mesh creation - accounts for PyVista ordering"""
        # Surface elements come first in merged mesh
        surface_cell_idx = 0
        for eid,elem in self.model_data.bdf.elements.items():
            if elem.type in ["CQUAD4", "CTRIA3"]:
                self.element_to_cell_map[eid] = surface_cell_idx
                surface_cell_idx += 1
        
        # Line elements come after surface elements
        line_cell_idx = surface_cell_idx  # Start where surface ended
        for eid,elem in self.model_data.bdf.elements.items():
            if elem.type == "CBAR":
                self.element_to_cell_map[eid] = line_cell_idx
                line_cell_idx += 1

    #BUGGGGGGGGGY!

    def colorize_by_property(self, model_data):
    #Colorize mesh elements by their property IDs with unique colors
        import matplotlib.colors as mcolors
        import random
        
        # Build array to hold actual PID values for each cell
        element_to_pid = np.full(self.mesh.n_cells, -1, dtype=int)
        missing_elements = []
        
        # First pass - collect all unique PIDs from the model
        all_pids = set()
        for eid in self.element_to_cell_map.keys():
            if eid in model_data.bdf.elements:
                pid = model_data.bdf.elements[eid].pid
                all_pids.add(pid)
        
        # Sort PIDs for consistent ordering
        unique_pids = sorted(list(all_pids))
        num_props = len(unique_pids)
        print(f"Found {num_props} unique property IDs")
        
        # Create mapping from PID to color index
        pid_to_index = {pid: idx for idx, pid in enumerate(unique_pids)}
        
        # Second pass - assign colors to elements
        el_pid_data = []  # For CSV export
        for eid, cell_idx in self.element_to_cell_map.items():
            if eid in model_data.bdf.elements:
                pid = model_data.bdf.elements[eid].pid
                color_idx = pid_to_index[pid]  # Get consistent color index
                element_to_pid[cell_idx] = color_idx  # Store color index, not PID
                
                el_pid_data.append({
                    "Element ID": eid,
                    "Property ID": pid,
                    "Color Index": color_idx,
                    "Type": model_data.bdf.elements[eid].type
                })
            else:
                missing_elements.append(eid)
                
        # Create custom colormap with distinct colors
        if num_props <= 10:
            # Use tab10 for up to 10 properties
            cmap = cm.get_cmap('tab10', num_props)
        elif num_props <= 20:
            # Use tab20 for up to 20 properties
            cmap = cm.get_cmap('tab20', num_props)
        else:
            # Generate evenly spaced HSV colors
            hsv_colors = []
            golden_ratio = (1 + 5 ** 0.5) / 2
            for i in range(num_props):
                hue = (i * golden_ratio) % 1
                hsv_colors.append((hue, 0.85, 0.9))
            colors = [mcolors.hsv_to_rgb(hsv) for hsv in hsv_colors]
        
        # Create custom colormap
        cmap = mcolors.ListedColormap(colors)
        
        # Store the color indices as scalars
        self.mesh.cell_data["Property Index"] = element_to_pid
        
        # Clear and redraw
        self.plotter.clear()
        self.add_axes()
        
        # Add mesh with property colors
        self.plotter.add_mesh(
            self.mesh,
            scalars="Property Index",
            show_edges=True,
            cmap=cmap,
            show_scalar_bar=False,
        )
        # Export mapping data
        df = pd.DataFrame(el_pid_data)
        df.to_csv("element_property_mapping.csv", index=False)
        
        if missing_elements:
            print(f"Warning: {len(missing_elements)} elements not found in BDF")
        
        self.plotter.reset_camera()
        self.plotter.render()

    def reset_view(self):
        """Reset the camera view"""
        self.plotter.reset_camera()
        self.plotter.update()
        
    def closeEvent(self, event):
        """Handle cleanup when widget is closed"""
        self.plotter.close()
        super().closeEvent(event)


    #öylesine xD
    def plot_something_random(self):
        import random
        
        example_datasets = dir(pv.examples)  # This gives you a list of available example datasets
        example_datasets = [dataset for dataset in example_datasets if not dataset.startswith('_')]
        random_example = random.choice(example_datasets)

        try:
            dataset = getattr(pv.examples, random_example)()  # Call the example function
            # Clear the previous plot (if any)
            self.plotter.clear()
            # Add the new dataset to the plotter
            self.plotter.add_mesh(dataset, show_edges=True, edge_color='black')
            # Optionally, reset camera to fit the new plot
            self.plotter.reset_camera()
            self.plotter.update()
        except Exception as e:
            print(f"Random plot failed {e}, trying again...")
            self.plot_something_random()

        # Plot the dataset
        self.has_rendered = True
        print(f"Plotting: {random_example}")
