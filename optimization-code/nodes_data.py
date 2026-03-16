from pyiron_workflow import as_function_node, as_macro_node
from pyiron_workflow import Workflow
import json
from typing import Any, Dict, Tuple, Optional
import pandas as pd
import re
import os
import shutil
import numpy as np
from pathlib import Path
import shutil

@as_function_node()
def yes_no(no_new_exps:bool)->str:
    answer='empty'
    if no_new_experiments==False:
        while answer!='y' or answer!='n':
            answer=input('Do you want to visualize the new experiments? (y/n)')
            print('Invalid answer. Write y or n.')
    return answer

@as_function_node()
def reorder_ids():
    """
    Reordena experimentos por fecha de creación usando metadata JSON.
    - Usa siempre la clave "Original Date".
    - Renumera IDs en experiments.json
    - Renombra archivos en metadata/, clean/ y raw/ si existen.
    """

    base_dir = Path.cwd()

    # Si existe una carpeta "data", trabajar allí
    if (base_dir / "data").exists():
        data_dir = base_dir / "data"
    else:
        data_dir = base_dir

    metadata_dir = data_dir / "metadata"
    clean_dir = data_dir / "clean"
    raw_dir = data_dir / "raw"
    json_path = data_dir / "experiments.json"

    # 1. Leer el json principal
    with open(json_path, "r") as f:
        experiments = json.load(f)

    # 2. Obtener fechas desde metadata
    exp_with_dates = []
    for exp in experiments:
        old_id = exp["id"]

        meta_file = metadata_dir / f"metadata{old_id}.json"
        if not meta_file.exists():
            raise FileNotFoundError(f"Falta metadata para experimento {old_id}")

        with open(meta_file, "r") as f:
            meta_data = json.load(f)

        if "Original Date" not in meta_data:
            raise ValueError(f"metadata{old_id}.json no tiene 'Original Date'")

        date = pd.to_datetime(meta_data["Original Date"])
        exp_with_dates.append((old_id, date, exp))

    # 3. Ordenar por fecha
    exp_with_dates.sort(key=lambda x: x[1])

    # 4. Crear nuevo mapping {old_id -> new_id}
    id_map = {old: new_id+1 for new_id, (old, _, _) in enumerate(exp_with_dates)}

    # 5. Renombrar archivos metadata, clean y raw
    for old_id, _, _ in exp_with_dates:
        new_id = id_map[old_id]

        # metadata
        old_meta = metadata_dir / f"metadata{old_id}.json"
        if old_meta.exists():
            new_meta = metadata_dir / f"metadata{new_id}.json"
            shutil.move(str(old_meta), str(new_meta))

        # clean
        old_clean = clean_dir / f"clean{old_id}.csv"
        if old_clean.exists():
            new_clean = clean_dir / f"clean{new_id}.csv"
            shutil.move(str(old_clean), str(new_clean))

        # raw
        old_raw = raw_dir / f"raw{old_id}.csv"
        if old_raw.exists():
            new_raw = raw_dir / f"raw{new_id}.csv"
            shutil.move(str(old_raw), str(new_raw))

    # 6. Actualizar IDs en el json principal
    new_experiments = []
    for new_id, (_, _, exp) in enumerate(exp_with_dates, start=1):
        exp["id"] = new_id
        new_experiments.append(exp)

    with open(json_path, "w") as f:
        json.dump(new_experiments, f, indent=2)

    return id_map

@as_function_node()
def no_new_experiments(new_experiments:list)->bool:
    return len(new_experiments)==0

@as_function_node()
def graph_experiments(exp_list:list,no_new_exps:bool,vis:str,clean_dir:str='data/clean'):
    if no_new_exps == False and vis== "y":
            for exp in exp_list:
                print(f"Visualization experiment number {exp['id']} ({exp['filename']})")
                path = os.path.join(clean_dir, f"data{exp['id']}.csv")
                df = pd.read_csv(path)

                #graph visualization

                current_cols = [col for col in df.columns if col.startswith('I_')]

                plt.figure(figsize=(10,6))
            
                for col in current_cols:
                    plt.plot(df['Time'], df[col], label=col)
            
                plt.xlabel('Time')
                plt.ylabel('Current')
                
                plt.title('Currents vs Time')
                plt.legend(loc='right', fontsize='small', ncol=2,bbox_to_anchor=(1.3, 0.5))
                plt.grid(True)
                plt.show()


                next=True
                while next:
                    answer=input("What do you want to visualize next? (colx/rowx/enter)")
                    if answer.startswith("col"):
                        try:
                            col_n = int(answer[3:])
                            #graph_col
                            col_name='I_('+str(col_n)
                            current_cols = [col for col in df.columns if col.startswith(col_name)]
                        
                            plt.figure(figsize=(10,6))
                        
                            for col in current_cols:
                                plt.plot(df['Time'], df[col], label=col)
                        
                            plt.xlabel('Time')
                            plt.ylabel('Current')
                            plt.title(f'Currents vs Time col {col_n}')
                            plt.legend(loc='right', fontsize='small', ncol=2,bbox_to_anchor=(1.3, 0.5))
                            plt.grid(True)
                            plt.show()
                        
                        except ValueError:
                            print("Invalid column number.")
                    
                    elif answer.startswith("row"):
                        try:
                            row_n = int(answer[3:])
                            #graph_row

                            row_name=str(row_n)+')'
                            current_cols = [col for col in df.columns if col.endswith(row_name)]
                            plt.figure(figsize=(10,6))
                        
                            for col in current_cols:
                                plt.plot(df['Time'], df[col], label=col)
                        
                            plt.xlabel('Time')
                            plt.ylabel('Current')
                            plt.title(f'Currents vs Time row {row_n}')
                            plt.legend(loc='right', fontsize='small', ncol=2,bbox_to_anchor=(1.3, 0.5))
                            plt.grid(True)
                            plt.show()
                            
                        except ValueError:
                            print("Invalid row number.")
                    else:
                        next=False
                        
@as_macro_node()
def visualization(self,new_experiments:list,CLEAN_DIR='data/clean'):

    self.no_new_experiments=no_new_experiments(new_experiments=new_experiments)
        
    self.answer=yes_no(no_new_exps=self.no_new_experiments)

    self.graphs=graph_experiments(no_new_exps=self.no_new_experiments,vis=self.answer,clean_dir=CLEAN_DIR,exp_list=new_experiments)



@as_function_node()
def load_summary(SUMMARY_PATH:str="data/experiments.json") -> list: #receives the summary paths and returns the list with the experiments
    if os.path.exists(SUMMARY_PATH) and os.path.getsize(SUMMARY_PATH) > 0:
        with open(SUMMARY_PATH, 'r') as f:
            summary =json.load(f)
    else:
        summary=[]
    return summary

@as_function_node()
def save_summary(summary:list,SUMMARY_PATH:str="data/experiments.json"): #saves the json
    with open(SUMMARY_PATH, 'w') as f:
        json.dump(summary, f, indent=4)

@as_function_node()
def next_experiment(summary_last:list)->int: #obtains the new id for the next experiment
    if len(summary_last)==0:
        n=1
    else:
        n=max(exp["id"] for exp in summary_last) + 1
    return n

@as_function_node("metadata","df")
def open_data(route:str) -> tuple[dict,pd.DataFrame]: #Function where we insert the route to the txt file and returns the data (pandas df) and the metadata (dictionary)
    data_start=False
    dataset=[]
    metadata={}
    if route!='empty':
        with open(route, "r", encoding="utf-8") as f:
            for line in f:
    
                #First we check if we have arrived to the data (if the line starts with Time)
                if line.startswith('"Time"'): 
                    columns = line.strip().split('\t')
                    columns=[item.strip('"').strip() for item in columns]
                    dataset.append(columns)
                    data_start = True
                    continue
                if data_start:
                    row = line.strip().split('\t')
                    row = [row[0]] + [float(x) for x in row[1:]] #We transform the data from string to float
                    dataset.append(row)
    
                #Collect the metadata
                else:
                    line=re.split(r':', line.strip())
                    line=[item.strip('"').strip(':').strip() for item in line]
                    if len(line)==1:
                        if line[0]=='Exp Name': #If the experiment has no name, we fixe it to None
                            line.append('None')
                            metadata[line[0]]=line[1]
                    else:
                        if line[0]=='Data File' or line[0]=='Original File': #The C was splitted from the route
                            line[1]=line[1]+line[2]
                        elif line[0]=='Original Date': #The hour got splitted
                            line[1]+=':'+line[2]+':'+line[3]
                        try:
                            line[1]=float(line[1])
                        except:
                            pass
                        metadata[line[0]]=line[1]
    
    
            df = pd.DataFrame(dataset[1:], columns=dataset[0])
            df['Time'] = df['Time'].astype(float) 
    else:
        df=pd.DataFrame(dataset)
    return metadata, df

@as_function_node
def check_summary(summary_check:list, RAW_DIR:str='data/raw', META_DIR:str='data/metadata', CLEAN_DIR:str='data/clean')->tuple[list[int],list[int],list[int]]: 
    raw, meta, clean= [], [], []  #generates three list that contain the experiments that are missing from each folder
    for exp in summary_check:
        fid = exp["id"]
        fname = exp["filename"]
        raw_path = os.path.join(RAW_DIR, fname)
        meta_path = os.path.join(META_DIR, f"metadata{fid}.json")
        clean_path = os.path.join(CLEAN_DIR, f"data{fid}.csv")

        if not os.path.exists(raw_path):
            raw.append(fid)
            continue
            
        if not os.path.exists(meta_path):
            meta.append(fid)

        if not os.path.exists(clean_path):
            clean.append(fid)
    if len(raw)==0:
        raw=[-1]
    if len(clean)==0:
        clean=[-1]
    if len(meta)==0:
        meta=[-1]
    
    return raw, meta, clean

@as_function_node
def obtain_filename(n:int,summary:list,RAW_DIR:str='data/raw') -> str: #given an id, obtains the filename of the experiment
    if n==-1:
        filename='empty'
    else:
        filename=os.path.join(RAW_DIR, next(entry['filename'] for entry in summary if entry['id'] == n))
    return filename

@as_function_node
def save_clean(df_clean:pd.DataFrame, id_clean:int,CLEAN_DIR:str='data/clean'): #given a df and the id of the experiment, saves it
    if not df_clean.empty:
        clean_path = os.path.join(CLEAN_DIR, f"data{id_clean}.csv")
        df_clean.to_csv(clean_path, index=False)

@as_function_node
def save_metadata(metadata:dict, id_metadata:int, META_DIR:str='data/metadata'): #given the metadata and the id of the experiment, saves it
    if metadata:
        meta_path = os.path.join(META_DIR, f"metadata{id_metadata}.json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=4)

@as_macro_node()
def repair_clean(self, missing_n:int, summary_repair:list, RAW_DIR:str='data/raw', CLEAN_DIR:str='data/clean'): #given the id of an experiment, fixes the missing clean
    
    self.file_route_clean=obtain_filename(n=missing_n,summary=summary_repair)
        
    self.opener_clean=open_data(route=self.file_route_clean)
    
    self.saver_clean=save_clean(df_clean=self.opener_clean.outputs.df,id_clean=missing_n)

    return None

@as_macro_node()
def repair_metadata(self, missing_n:int, summary_repair:list, RAW_DIR:str='data/raw', META_DIR:str='data/metadata'): #given the id of an experiment, fixes the missing metadata
    
    self.file_route_metadata=obtain_filename(n=missing_n,summary=summary_repair)
        
    self.opener_metadata=open_data(route=self.file_route_metadata)
    
    self.saver_metadata=save_metadata(metadata=self.opener_metadata.outputs.metadata,id_metadata=missing_n)

    return None

@as_function_node()
def repair_raw(summary_repair:list, missing_raw:list, META_DIR:str='data/metadata', CLEAN_DIR:str='data/clean') ->list: #given a list of the missing raw, deletes its 
    if missing_raw!=[-1]:
        for id_exp in missing_raw:                                                                      #corresponding metadata and clean data and reorganizes IDs
            meta_path = os.path.join(META_DIR, f"metadata{id_exp}.json")
            clean_path = os.path.join(CLEAN_DIR, f"data{id_exp}.csv")
            for path in [meta_path, clean_path]:
                    if os.path.exists(path):
                        os.remove(path)
        
        summary_valid=[entry for entry in summary_repair if entry['id'] not in missing_raw]
        new_summary = []
            
        for new_id, entry in enumerate(summary_valid, start=1):
            old_id = entry['id']
            
        
            old_meta = os.path.join(META_DIR, f"metadata{old_id}.json")
            new_meta = os.path.join(META_DIR, f"metadata{new_id}.json")
        
            old_clean = os.path.join(CLEAN_DIR, f"data{old_id}.csv")
            new_clean = os.path.join(CLEAN_DIR, f"data{new_id}.csv")
        
            os.rename(old_meta, new_meta)
            os.rename(old_clean, new_clean)
        
            new_entry = entry.copy()
            new_entry['id'] = new_id
            new_summary.append(new_entry)
    else:
        new_summary=summary_repair
    return new_summary

@as_macro_node()
def check_and_repair_summary(self, summary:list, RAW_DIR:str='data/raw', META_DIR:str='data/metadata', CLEAN_DIR:str='data/clean') -> list:
    
    self.checker= check_summary(summary_check=summary)
    #We have to check if clean is correct. if its correct, the node receives [-1] and does nothing
    self.clean_repairer= Workflow.create.for_node(body_node_class=repair_clean,
                                                  iter_on='missing_n',
                                                  missing_n=self.checker.outputs.clean,
                                                  summary_repair=summary)
    
    #idem for metadata
    self.metadata_repairer= Workflow.create.for_node(body_node_class=repair_metadata,
                                                  iter_on='missing_n',
                                                  missing_n=self.checker.outputs.meta,
                                                  summary_repair=summary)
   
    
    #idem for raw
    self.raw_repairer= repair_raw(summary_repair=summary, missing_raw=self.checker.outputs.raw)

    self.saver= save_summary(summary=self.raw_repairer)

    return self.raw_repairer

@as_function_node()
def new_data(summary:list, RAW_DIR:str='data/raw') ->list: #gets the list of new filenames that need to be processed
    processed_names = {entry['filename'] for entry in summary}
    all_files = [f for f in os.listdir(RAW_DIR) if f.endswith(".txt") and f not in processed_names]
    all_files = sorted(all_files,key=lambda f: os.path.getctime(os.path.join(RAW_DIR, f)))
    if len(all_files)==0:
        all_files=[-1]
    return all_files

@as_function_node()
def tuple_experiments(first_n:int, experiments:list)->list[tuple]:
    if experiments==[-1]:
        list_tuples=[(-1,-1)]
    else:
        list_tuples=[]
        for i in range(first_n,first_n+len(experiments)):
            list_tuples.append((i,experiments[i-first_n]))
    return list_tuples

@as_function_node()
def get_concentrations(filename)->tuple[float,float]:
    if filename!=-1:
        match = re.match(r"(\d+)uM_CeN_(\d+)uM_NaFu.*\.txt", filename)
        if match:
            c1,c2= float(match.group(1)), float(match.group(2))
            c1=c1/1000000
            c2=c2/1000000
        else:
            c1,c2= None,None
    else:
        c1,c2= -1,-1
        c1=float(c1)
        c2=float(c2)
    return c1,c2

@as_function_node()
def path_maker(filename,route:str)->str:
    if filename==-1:
        path_exp='empty'
    else:
        path_exp=os.path.join(route,filename)
    return path_exp

@as_function_node()
def experiment_separator(tuple_sep:tuple):
    id_exp= tuple_sep[0]
    filename_exp= tuple_sep[1]
    return id_exp, filename_exp

@as_function_node()
def save_experiment(id_exp:int, c1:float, c2:float, filename_exp) ->dict:
    if c1==-1:
        exp_info={}
    else:
        exp_info={
                "id": id_exp,
                "c1": c1,
                "c2": c2,
                "filename": filename_exp
            }
    return exp_info

@as_macro_node()
def add_new_data(self,exp_tuple:tuple,  RAW_DIR:str='data/raw', META_DIR:str='data/metadata', CLEAN_DIR:str='data/clean') -> dict:
    
    self.separator=experiment_separator(tuple_sep=exp_tuple)
    
    self.route_raw=path_maker(filename=self.separator.outputs.filename_exp, route=RAW_DIR)
    
    self.opener=open_data(route=self.route_raw)

    self.concentrations=get_concentrations(filename=self.separator.outputs.filename_exp)

    self.metadata_saver=save_metadata(metadata=self.opener.outputs.metadata,id_metadata=self.separator.outputs.id_exp)

    self.clean_saver=save_clean(df_clean=self.opener.outputs.df, id_clean=self.separator.outputs.id_exp)

    self.experiment_saver= save_experiment(id_exp=self.separator.outputs.id_exp, filename_exp=self.separator.outputs.filename_exp, c1=self.concentrations.outputs.c1, c2=self.concentrations.outputs.c2)

    return self.experiment_saver

@as_function_node()
def add_new_experiments(old_exp:list,new_exp:list)->list:
    for exp in new_exp:
        if exp:
            old_exp.append(exp)
    return old_exp

@as_function_node()
def save_updated_experiments(data, filename="updated_experiments.pkl"):
    import pickle
    print(data)
    with open(filename, "wb") as f:
        pickle.dump(data, f)


@as_macro_node()
def process_data(self,SUMMARY_PATH:str="data/experiments.json"):
    
    self.loader=load_summary()
    
    self.checker_and_repair=check_and_repair_summary(summary=self.loader)
    
    self.data_to_process= new_data(summary=self.checker_and_repair)

    self.next_n= next_experiment(summary_last=self.checker_and_repair)
    
    self.tuple_generator=tuple_experiments(first_n=self.next_n, experiments=self.data_to_process)

    self.new_data_processor= Workflow.create.for_node(
            body_node_class=add_new_data,
            iter_on="exp_tuple",
            exp_tuple=self.tuple_generator,
            output_as_dataframe=False
        )

    self.visualize=visualization(new_experiments=self.new_data_processor.outputs.experiment_saver)

    self.add_new=add_new_experiments(old_exp=self.checker_and_repair, new_exp=self.new_data_processor.outputs.experiment_saver)

    save_updated_experiments(self.add_new)

    self.saver=save_summary(summary=self.add_new)

    return self.add_new
    

if __name__ == "__main__":
    wf = Workflow("gen_structures")
    wf.save_data=(process_data())
    wf.run()

    
    
