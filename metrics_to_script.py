import os
import re
import pickle
import numpy as np
import pandas as pd



CLEAN_DIR = "data/clean"
EXPERIMENTS_PKL = "updated_experiments.pkl"
OUT_CSV = "normalized_dataframe_new.csv"
OUT_PKL = "normalized_dataframe_new.pkl"



TIME_IN = 17970
WINDOW = 50
THRESHOLD = 5e-6
constant_t_eff_input=True


with open(EXPERIMENTS_PKL, "rb") as f:
    updated_summary = pickle.load(f)

print(f"Loaded {len(updated_summary)} experiments from {EXPERIMENTS_PKL}")


c1_max=max([exp["c1"] for exp in updated_summary])

list_deltas = []
list_c1_alphas = []

for exp in updated_summary:
    exp_id = exp["id"]
    c1 = exp["c1"]
    c2 = exp["c2"]
    c1_alpha=c1/c1_max

    # read csv
    data_path = os.path.join(CLEAN_DIR, f"data{exp_id}.csv")
    df = pd.read_csv(data_path)

    # electrode columns (deterministic order)
    cols = [col for col in df.columns if col.startswith("I_")]




    df["Time"] = [int(x) for x in df["Time"].values]



    #print(f"\nexp {exp_id}: df shape={df.shape}, electrodes={len(cols)}")
    #print("first electrodes:", cols[:10])

    #compute delta and c1_alpha for each electrode
    deltas = []
    c1_alphas = []
    c1_alphas.append(float(c1_alpha))

    times = np.asarray(df["Time"].values)
    idx_in = int(np.argmin(np.abs(times - TIME_IN))) #find id of t_inhibitor in
    punishment=-0.5  #change this for punishment
    
    for electrode in cols: #iterate for each electrode
        current = np.asarray(df[electrode].values)
        I_start = current[idx_in]
        end = False
        i=1
        while I_start == 0:
            I_start = current[idx_in+i] #inhibitor input current
            if i>=50:
                break
            i+=1
        
 
        delta = -29.0      #fallback value, if this occurs there is something wrong


        #new delta calculation for constant t_eff_input
        if constant_t_eff_input:
            I_stable=current[len(current)-1]
            i=2
            while I_stable == 0 and end is False:
                I_stable = current[len(current)-i]
                if i>=(len(current)-TIME_IN-5):
                    if I_stable == 0 and I_start != 0:
                        delta = punishment   #punishment
                        end=True
                    elif I_stable == 0 and I_start == 0:
                        delta = -30 #remove data
                        end = True
                i+=1
            if abs(I_start)>abs(I_stable) and I_start!=0 and I_stable!=0:
                delta = np.log10(abs(I_start) / abs(I_stable))
                end = True
            elif abs(I_start)<abs(I_stable) and I_start!=0 and I_stable!=0:
                delta = punishment
                end = True
            elif abs(I_stable) == abs(I_start):
                delta = -30 
            elif I_stable != 0 and I_start == 0:
                print(I_stable, I_start)
                delta = -100
                end = True
        deltas.append(float(delta))


    dic_deltas = {"id": exp_id, "c1": c1, "c2": c2, "c1_alpha": c1_alpha}

    dic_deltas.update({cols[i]: deltas[i] for i in range(min(15, len(cols)))})
    list_deltas.append(dic_deltas)



df_deltas = pd.DataFrame(list_deltas)
#print(df_deltas)



data = df_deltas.iloc[:, 4:]
#print(data)
# Replace -30 or -1 with NaN (ignored in mean)
data = data.replace(-30, np.nan)
#data = data.replace(-0.5, np.nan)

# Replace 10 with the maximum value in the dataset
max_val = data.max().max()
data = data.replace(10, max_val)
#print(data)
# Compute row-wise mean ignoring NaN
df_deltas["mean_delta"] = data.mean(axis=1)


df_deltas_final = df_deltas[["id", "c1", "c2", "mean_delta","c1_alpha"]]
#print(df_deltas_final)




# SAVE OUTPUTS
normalized_dataframe=df_deltas_final
normalized_dataframe.to_csv(OUT_CSV, index=False)
with open(OUT_PKL, "wb") as f:
    pickle.dump(normalized_dataframe, f)

print(f"\nSaved:\n- {OUT_CSV}\n- {OUT_PKL}")
print("\nPreview:")
print(normalized_dataframe.head(10))