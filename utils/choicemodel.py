import pickle
import numpy as np
from joblib import Parallel, delayed
from scipy.optimize import curve_fit
from scipy.io import loadmat
from utils.eval import gen_behav_models

def softmax(x: np.array, T=1e-3) -> np.array:
    """softmax non-linearity

    Args:
        x (np.array): inputs to softmax
        T (float, optional): softmax temperature. Defaults to 1e-3.

    Returns:
        np.array: outputs of softmax
    """

    return np.exp(x / T) / (np.exp(x / T) + np.exp(0 / T))


def choice_sigmoid(x: np.array, T=1e-3) -> np.array:
    """applies sigmoid to inputs

    Args:
        x (np.array): array of numbers
        T (float, optional): temperature (slope of sigmoid). Defaults to 1e-3.

    Returns:
        np.array: outputs of sigmoid
    """
    cc = np.clip(-x / T, -709.78, 709.78).astype(np.float64)
    sigm = 1.0 / (1.0 + np.exp(cc))
    return sigm


def mse(x: np.array, y: np.array) -> float:
    """mean squared error between two vectors

    Args:
        x (np.array): a vector of floats
        y (np.array): a vector of floats

    Returns:
        float: the mse between x and y
    """
    mse = np.mean(np.sqrt((x - y) ** 2))
    return mse


def compute_mse(
    y_sub: np.array,
    i_slug: int,
    i_temp: int,
    slug_vals=np.round(np.linspace(0.05, 1, 20), 2),
    temp_vals=np.logspace(np.log(0.1), np.log(4), 20),
    n_runs=50,
    curriculum="interleaved",
) -> np.array:
    """computes mse between human and model choices

    Args:
        y_sub (np.array): choices made by a single human participant (task a & b concatenated)
        i_slug (int): index of sluggishness value to fit
        i_temp (int): index of temperature value to fit
        slug_vals (np.array, optional): sluggishness values to use. Defaults to np.round(np.linspace(0.05,1,20),2).
        temp_vals (np.array, optional): sigmoid temperature values to use. Defaults to np.logspace(np.log(0.1),np.log(4),20).
        n_runs (int, optional): number of runs to include. Defaults to 50
        curriculum (str, optional): training curriculum (blocked or interleaved). Defaults to interleaved

    Returns:
        np.array: mse for current fit
    """

    # load models with requested sluggishness value and average over outputs
    curric_str = (
        "sluggish_oja_int_select_sv"
        if curriculum == "interleaved"
        else "sluggish_oja_blocked_select_sv"
    )
    y_net = []
    for r in np.arange(0, n_runs):
        with open(
            "../checkpoints/"
            + curric_str
            + str(i_slug)
            + "/run_"
            + str(r)
            + "/results.pkl",
            "rb",
        ) as f:
            results = pickle.load(f)
            y = choice_sigmoid(results["all_y_out"][1, :, :], T=temp_vals[i_temp])
            y_net.append(y)
    y_net = np.array(y_net).mean(0)
    assert len(y_net) == 50

    # pass averaged outputs through sigmoid with chosen temp value
    # y_net = choice_sigmoid(y_net, T=temp_vals[i_temp])

    # compute and return mse between human and simulated model choices
    return mse(y_sub, y_net)


def gridsearch_modelparams(
    y_sub: np.array, n_jobs=-1, curriculum="interleaved"
) -> np.array:
    """performs grid search over softmax temperature and
       sluggishness param

    Args:
        y_sub (np.array): vector with choice probabilities of single subject
        n_jobs (int, optional): number of parallel jobs. Defaults to -1
        curriculum (str, optional): training curriculum (blocked or interleaved). Defaults to interleaved

    Returns:
        np.array: grid of MSE vals for each hp combination
    """
    sluggish_vals = np.round(np.linspace(0.05, 1, 20), 2)
    temp_vals = np.logspace(np.log(0.1), np.log(4), 20)
    idces_sluggishness = np.arange(0, len(sluggish_vals))
    a, b = np.meshgrid(idces_sluggishness, idces_sluggishness)
    a, b = a.flatten(), b.flatten()
    if n_jobs > 1:
        mses = Parallel(n_jobs=-1, backend="loky", verbose=1)(
            delayed(compute_mse)(
                y_sub, i_slug, i_temp, n_runs=20, curriculum=curriculum
            )
            for i_slug, i_temp in zip(a, b)
        )
    else:
        mses = [
            compute_mse(y_sub, i_slug, i_temp, n_runs=20, curriculum=curriculum)
            for i_slug, i_temp in zip(a, b)
        ]
    return mses


def wrapper_gridsearch_modelparams(single_subs=True) -> dict:
    """wrapper for gridsearch of modelparams
    Args:
        single_subs (bool, optional): whether or not to fit to individual participants. Defaults to True
    Returns:
        dict: mse for blocked and interleaved groups
    """

    cmats = loadmat("../datasets/choicemats_exp1a.mat")
    keys = ["cmat_b", "cmat_i"]
    results = {}
    for k in keys:
        if k.split("_")[-1] == "b":
            curriculum = "blocked"
        elif k.split("_")[-1] == "i":
            curriculum = "interleaved"
        if single_subs:
            mses = []
            for c in range(len(cmats[k + "_north"])):
                y_sub = np.concatenate(
                    (
                        cmats[k + "_north"][c, :, :].ravel(),
                        cmats[k + "_south"][c, :, :].ravel(),
                    ),
                    axis=0,
                )[:, np.newaxis]
                assert len(y_sub) == 50
                mses.append(gridsearch_modelparams(y_sub, curriculum=curriculum))
        else:
            y_sub = np.concatenate(
                (
                    cmats[k + "_north"].mean(0).ravel(),
                    cmats[k + "_south"].mean(0).ravel(),
                ),
                axis=0,
            )[:, np.newaxis]
            assert len(y_sub) == 50
            mses = gridsearch_modelparams(y_sub, curriculum=curriculum)
        results[k] = np.asarray(mses)
    return results


def sample_choices(y_est: np.array, n_samp=10000) -> np.array:
    """samples choices from sigmoidal inputs

    Args:
        y_est (np.array): array with choice probabilities
        n_samp (int, optional): number of samples to draw. Defaults to 1000.

    Returns:
        np.array: sampled choices
    """
    sampled_choices = np.array(
        [y_est > np.random.rand(*y_est.shape) for i in range(n_samp)]
    )
    return sampled_choices


# sampled_choices = sample_choices(cmats_a)


def compute_sampled_accuracy(cmat_a: np.array, cmat_b: np.array) -> float:
    """computes accuracy based on choices sampled from sigmoid

    Args:
        cmat_a (np.array): estimated choice matrix for task a
        cmat_b (np.array): esimated choie matrix for task b

    Returns:
        float: computed accuracy
    """
    # generate ground truth matrices:
    _, _, cmats = gen_behav_models()
    cmat_gt_a = cmats[0, 0, :, :]
    cmat_gt_b = cmats[0, 1, :, :]
    # indices of non-boundary trials:
    valid_a = np.where(cmat_gt_a.ravel() != 0.5)
    valid_b = np.where(cmat_gt_b.ravel() != 0.5)
    # sample choices
    cmat_samp_a = sample_choices(cmat_a)
    cmat_samp_b = sample_choices(cmat_b)
    # calculate accuracy for each sample, excluding boundary trials
    accs_a = [
        np.mean(cmat_gt_a.ravel()[valid_a] == samp.ravel()[valid_a])
        for samp in cmat_samp_a
    ]
    accs_b = [
        np.mean(cmat_gt_b.ravel()[valid_b] == samp.ravel()[valid_b])
        for samp in cmat_samp_b
    ]
    return (np.mean(accs_a) + np.mean(accs_b)) / 2


# scratchpad


def nolapse(func):
    """decorator for sigmoid_fourparmas to avoid fitting lapse rate"""

    def inner(x, L, k, x0):
        return func(x, L, k, x0, fitlapse=False)

    return inner


def sigmoid_fourparams(
    x: np.array, L: float, k: float, x0: float, fitlapse=True
) -> np.array:
    """sigmoidal non-linearity with four free params

    Args:
        x (np.array): inputs
        L (float): lapse rate
        k (float): slope
        x0 (float): offset
        fitlapse (bool, optional): fit lapse rate. Defaults to True.

    Returns:
        np.array: outputs of sigmoid
    """
    if fitlapse == False:
        L = 0
    y = L + (1 - L * 2) / (1.0 + np.exp(-k * (x - x0)))
    return y


def fit_sigmoid(x: np.array, y, fitlapse=True):
    """
    fits sigmoidal nonlinearity to some data
    returns best-fitting parameter estimates
    """
    # initial guesses for max, slope and inflection point
    theta0 = [0.0, 0.0, 0.0]
    if fitlapse == False:
        popt, _ = curve_fit(
            nolapse(sigmoid_fourparams),
            x,
            y,
            theta0,
            method="dogbox",
            maxfev=1000,
            bounds=([0, -10, -10], [0.5, 10, 10]),
        )
    else:
        popt, _ = curve_fit(
            sigmoid_fourparams,
            x,
            y,
            theta0,
            method="dogbox",
            maxfev=1000,
            bounds=([0, -10, -10], [0.5, 10, 10]),
        )

    return popt