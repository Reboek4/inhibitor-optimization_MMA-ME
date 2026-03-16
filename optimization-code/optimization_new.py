import optuna
from optuna.samplers import NSGAIISampler
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score

optuna.logging.set_verbosity(optuna.logging.WARNING)


def make_objective(model_delta, model_teff):
    def objective(trial):
        conc1 = trial.suggest_float("c1", 1e-5, 2e-3, step=1e-5)
        conc2 = trial.suggest_float("c2", 1e-5, 2e-3, step=1e-5)

        input_data = pd.DataFrame([[conc1, conc2]], columns=["c1", "c2"])
        delta_mean_pred = float(model_delta.predict(input_data)[0])
        teff_mean_pred = float(model_teff.predict(input_data)[0])

        # directions later are ["maximize", "minimize"]
        return delta_mean_pred, teff_mean_pred

    return objective


def optimize_rf(X, y, n_trials=100, random_state=42):
    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 300),
            "max_depth": trial.suggest_int("max_depth", 3, 20),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 10),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
            "max_features": trial.suggest_categorical("max_features", [None, "sqrt", "log2"]),
        }

        model = RandomForestRegressor(**params, random_state=random_state, n_jobs=-1)

        # Neg MSE: higher is better
        score = cross_val_score(model, X, y, cv=3, scoring="neg_mean_squared_error").mean()
        return float(score)

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)
    return study.best_params


def get_X_Y(parameters_sep: pd.DataFrame):
    X = parameters_sep[["c1", "c2"]]
    y_delta = parameters_sep["mean_delta"].values
    y_c1_alpha = parameters_sep["c1_alpha"].values
    return X, y_delta, y_c1_alpha


def train_models(X, y_delta, y_c1_alpha, rf_opt_trials=100):
    params_delta = optimize_rf(X, y_delta, n_trials=rf_opt_trials)
    params_c1_alpha = optimize_rf(X, y_c1_alpha, n_trials=rf_opt_trials)

    model_delta = RandomForestRegressor(**params_delta, random_state=42, n_jobs=-1).fit(X, y_delta)
    model_c1_alpha = RandomForestRegressor(**params_c1_alpha, random_state=42, n_jobs=-1).fit(X, y_c1_alpha)

    return model_delta, model_c1_alpha, params_delta, params_c1_alpha


def optuna_optimization(model_delta, model_c1_alpha, n_trials=500):
    sampler = NSGAIISampler()
    study = optuna.create_study(directions=["maximize", "minimize"], sampler=sampler)
    study.optimize(make_objective(model_delta, model_c1_alpha), n_trials=n_trials)

    # Deduplicate best_trials by (c1,c2)
    unique_params = set()
    unique_trials = []

    for trial in study.best_trials:
        param_tuple = tuple(round(trial.params.get(k, 0.0), 12) for k in ["c1", "c2"])
        if param_tuple not in unique_params:
            unique_params.add(param_tuple)
            unique_trials.append(trial)

    # Sort: highest predicted_delta first
    unique_trials.sort(key=lambda t: t.values[0], reverse=True)

    rows = []
    for trial in unique_trials:
        rows.append(
            {
                "c1": float(trial.params["c1"]),
                "c2": float(trial.params["c2"]),
                "predicted_delta": float(trial.values[0]),
                "predicted_c1_alpha": float(trial.values[1]),
            }
        )

    df = pd.DataFrame(rows)

    # weights
    w_delta = 1.0
    w_alpha = 0.5   # adjust importance of minimizing c1_alpha

    df["score"] = w_delta * df["predicted_delta"] - w_alpha * df["predicted_c1_alpha"]

    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    df.insert(0, "Trial", df.index)

    return df, study


def main():



    parameters = pd.read_csv("normalized_dataframe_new.csv")

    required = {"c1", "c2", "mean_delta", "c1_alpha"}
    missing = required - set(parameters.columns)
    if missing:
        raise ValueError(f"parameters dataframe missing columns: {missing}")

    # 2) Split into X and y
    X, y_delta, y_c1_alpha = get_X_Y(parameters)

    # 3) Train two RF models (with optuna RF hyperparameter tuning)
    model_delta, model_c1_alpha, best_params_delta, best_params_c1_alpha = train_models(
        X, y_delta, y_c1_alpha, rf_opt_trials=100
    )

    print("\nBest RF params (delta):", best_params_delta)
    print("Best RF params (c1_alpha) :", best_params_c1_alpha)
    print(X,y_delta,y_c1_alpha)
    # 4) Multi-objective optuna search: maximize delta, minimize c1_alpha
    new_conc_df, study = optuna_optimization(model_delta, model_c1_alpha, n_trials=500)

    print("\nPareto candidates (deduplicated, sorted by predicted_delta desc):")
    print(new_conc_df)

    # 5) Save results
    new_conc_df.to_csv("best_concentrations.csv", index=False)
    print("\nSaved: best_concentrations.csv")



if __name__ == "__main__":
    main()
