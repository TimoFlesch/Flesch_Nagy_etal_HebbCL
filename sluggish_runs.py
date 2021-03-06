import torch
from pathlib import Path

import numpy as np
from utils.data import make_blobs_dataset, make_trees_dataset
from utils.nnet import get_device

from hebbcl.logger import MetricLogger1Hidden, LoggerFactory
from hebbcl.model import Nnet, ModelFactory
from hebbcl.trainer import Optimiser, train_on_blobs, train_on_trees
from hebbcl.parameters import parser
from joblib import Parallel, delayed

args = parser.parse_args()
# overwrite cuda argument depending on GPU availability
args.cuda = args.cuda and torch.cuda.is_available()

def execute_run_trees(i_run):
    print("run {} / {}".format(str(i_run), str(args.n_runs)))

    # create checkpoint dir
    run_name = "run_" + str(i_run)
    save_dir = Path("checkpoints") / args.save_dir / run_name

    # get (cuda) device
    args.device, _ = get_device(args.cuda)

    # trees settings
    args.n_episodes = 100
    args.n_layers = 2
    args.n_hidden = 100
    args.n_features = 974

    # get dataset
    dataset = make_trees_dataset(args, filepath="./datasets/")

    # instantiate logger, model and optimiser
    logger = LoggerFactory.create(args, save_dir)
    model = ModelFactory.create(args)
    optim = Optimiser(args)

    # send model to GPU
    model = model.to(args.device)

    # train model
    train_on_trees(args, model, optim, dataset, logger)

    # save results
    if args.save_results:
        save_dir.mkdir(parents=True, exist_ok=True)
        logger.save(model)


def execute_run(i_run):
    print("run {} / {}".format(str(i_run), str(args.n_runs)))

    # create checkpoint dir
    run_name = "run_" + str(i_run)
    save_dir = Path("checkpoints") / args.save_dir / run_name

    # get (cuda) device
    args.device, _ = get_device(args.cuda)

    # get dataset
    dataset = make_blobs_dataset(args)

    # instantiate logger, model and optimiser
    logger = MetricLogger1Hidden(save_dir)
    model = Nnet(args)
    optim = Optimiser(args)

    # send model to GPU
    model = model.to(args.device)

    # train model
    train_on_blobs(args, model, optim, dataset, logger)

    # save results
    if args.save_results:
        save_dir.mkdir(parents=True, exist_ok=True)
        logger.save(model)


if __name__ == "__main__":

    # # BASELINE NETWORK -------------------------------------------------
    # args.cuda = False
    # args.ctx_scaling = 5
    # args.lrate_sgd = 0.2
    # args.lrate_hebb = 0.0093
    # args.weight_init = 1e-2
    # args.save_results = True
    # args.gating = "None"
    # args.perform_hebb = False
    # args.centering = False
    # args.verbose = False
    # args.ctx_avg = True
    # args.ctx_avg_type = "ema"
    # args.training_schedule = "interleaved"
    # args.n_runs = 50

    # sluggish_vals = np.linspace(0.05, 1, 20)
    # for ii, sv in enumerate(sluggish_vals):
    #     args.ctx_avg_alpha = sv
    #     args.save_dir = "sluggish_baseline_int_select_sv" + str(ii)
    #     Parallel(n_jobs=-1, verbose=10)(
    #         delayed(execute_run)(i_run) for i_run in range(args.n_runs)
    #     )

    # # OJA CTX NETWORK BLOCKED ---------------------------------------------
    # # overwrite standard parameters
    # args.cuda = False
    # args.ctx_scaling = 1
    # args.lrate_sgd = 0.03
    # args.lrate_hebb = 0.05
    # args.weight_init = 1e-2
    # args.save_results = True
    # args.gating = "oja_ctx"
    # args.centering = True
    # args.verbose = False
    # args.ctx_avg = True
    # args.ctx_avg_type = "ema"
    # args.training_schedule = "blocked"
    # args.n_runs = 20

    # sluggish_vals = np.linspace(0.05, 1, 20)
    # for ii, sv in enumerate(sluggish_vals):
    #     args.ctx_avg_alpha = sv
    #     args.save_dir = "sluggish_oja_blocked_select_sv" + str(ii)
    #     Parallel(n_jobs=6, verbose=10)(
    #         delayed(execute_run)(i_run) for i_run in range(args.n_runs)
    #     )

    # # OJA CTX NETWORK INTERLEAVED -----------------------------------------
    # # overwrite standard parameters
    # args.cuda = False
    # args.ctx_scaling = 1
    # args.lrate_sgd = 0.03
    # args.lrate_hebb = 0.05
    # args.weight_init = 1e-2
    # args.save_results = True
    # args.gating = "oja_ctx"
    # args.centering = True
    # args.verbose = False
    # args.ctx_avg = True
    # args.ctx_avg_type = "ema"
    # args.training_schedule = "interleaved"
    # args.n_runs = 20

    # sluggish_vals = np.linspace(0.05, 1, 20)
    # for ii, sv in enumerate(sluggish_vals):
    #     args.ctx_avg_alpha = sv
    #     args.save_dir = "sluggish_oja_int_select_sv" + str(ii)
    #     Parallel(n_jobs=6, verbose=10)(
    #         delayed(execute_run)(i_run) for i_run in range(args.n_runs)
    #     )

    # REVISION: OJA NETWORK BLOCKED ---------------------------------------------
    # # overwrite standard parameters
    # args.cuda = False
    # args.n_episodes = 8
    # args.ctx_scaling = 3
    # args.lrate_sgd = 0.09056499086887726
    # args.lrate_hebb = 0.002583861043525858
    # args.weight_init = 1e-2
    # args.save_results = True
    # args.perform_hebb = True
    # args.gating = "oja"
    # args.centering = True
    # args.verbose = False
    # args.ctx_avg = True
    # args.ctx_avg_type = "ema"
    # args.training_schedule = "blocked"
    # args.n_runs = 50

    # sluggish_vals = np.linspace(0.05, 1, 30)
    # for ii, sv in enumerate(sluggish_vals):
    #     args.ctx_avg_alpha = sv
    #     args.save_dir = "blobs_revision_8episodes_sluggish_blocked_oja_sv" + str(ii)
    #     Parallel(n_jobs=-1, verbose=10)(
    #         delayed(execute_run)(i_run) for i_run in range(args.n_runs)
    #     )

    # # REVISION: OJA NETWORK INTERLEAVED -----------------------------------------
    # # overwrite standard parameters
    # args.cuda = False
    # args.n_episodes = 8
    # args.ctx_scaling = 4
    # args.lrate_sgd = 0.09263634569936459
    # args.lrate_hebb = 0.0003276905554752727
    # args.weight_init = 1e-2
    # args.save_results = True
    # args.perform_hebb = True
    # args.gating = "oja"
    # args.centering = True
    # args.verbose = False
    # args.ctx_avg = True
    # args.ctx_avg_type = "ema"
    # args.training_schedule = "interleaved"
    # args.n_runs = 50

    # sluggish_vals = np.linspace(0.05, 1, 30)
    # for ii, sv in enumerate(sluggish_vals):
    #     args.ctx_avg_alpha = sv
    #     args.save_dir = "blobs_revision_8episodes_sluggish_interleaved_oja_sv" + str(ii)
    #     Parallel(n_jobs=-1, verbose=10)(
    #         delayed(execute_run)(i_run) for i_run in range(args.n_runs)
    #     )


    # REVISION: SLUGGISH TREES BLOCKED --------------------------------------------------
    # overwrite standard parameters
    args.cuda = False
    args.n_episodes = 100
    args.ctx_scaling = 4
    args.lrate_sgd = 0.00196874872857594
    args.lrate_hebb = 0.0008495631690508217
    args.weight_init = 1e-2
    args.save_results = True
    args.perform_hebb = True
    args.gating = "oja_ctx"
    args.centering = True
    args.verbose = False
    args.ctx_avg = True
    args.ctx_avg_type = "ema"
    args.training_schedule = "blocked"
    args.n_runs = 50

    sluggish_vals = np.linspace(0.05, 1, 30)
    for ii, sv in enumerate(sluggish_vals):
        args.ctx_avg_alpha = sv
        args.save_dir = "trees_revision_sluggish_blocked_oja_sv" + str(ii)
        Parallel(n_jobs=25, verbose=10)(
            delayed(execute_run_trees)(i_run) for i_run in range(args.n_runs)
        )

    # REVISION: SLUGGISH TREES INTERLEAVED ----------------------------------------------
    # overwrite standard parameters
    args.cuda = False
    args.n_episodes = 100
    args.ctx_scaling = 1
    args.lrate_sgd = 0.0018549176154984076
    args.lrate_hebb = 0.0066835760364487365
    args.weight_init = 1e-2
    args.save_results = True
    args.perform_hebb = True
    args.gating = "oja_ctx"
    args.centering = True
    args.verbose = False
    args.ctx_avg = True
    args.ctx_avg_type = "ema"
    args.training_schedule = "interleaved"
    args.n_runs = 50

    sluggish_vals = np.linspace(0.05, 1, 30)
    for ii, sv in enumerate(sluggish_vals):
        args.ctx_avg_alpha = sv
        args.save_dir = "trees_revision_sluggish_interleaved_oja_sv" + str(ii)
        Parallel(n_jobs=25, verbose=10)(
            delayed(execute_run_trees)(i_run) for i_run in range(args.n_runs)
        )
