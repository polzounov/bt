#!/usr/bin/env python3

import numpy as np
import gym
import os

from stable_baselines.common.vec_env.dummy_vec_env import DummyVecEnv
from stable_baselines.common.cmd_util import arg_parser
from stable_baselines.common import set_global_seeds
from stable_baselines import bench, logger

from student_env import StudentEnv
from stable_baselines import PPO2


def init_save_callback(logdir, batch_size, save_interval):
    def callback(
        _locals,
        _globals,
        logdir=logdir,
        batch_size=batch_size,
        save_interval=save_interval,
    ):
        """Save model every `save_interval` steps."""
        update_number = _locals["update"]  # Number of updates to policy
        step_number = update_number * batch_size  # Number of steps taken on environment

        # Note: for this to ever be true save_interval must be a multiple of batch_size
        if step_number % save_interval == 0:
            if not os.path.isdir(logdir + "/checkpoints"):
                os.makedirs(logdir + "/checkpoints")
            _locals["self"].save(logdir + "/checkpoints/{}".format(step_number))

        return True  # Returning False will stop training early

    return callback


def train(num_timesteps, logdir, save, save_interval, load, seed):
    def make_env():
        env_out = StudentEnv()
        env_out = bench.Monitor(env_out, logger.get_dir(), allow_early_resets=True)
        return env_out

    env = DummyVecEnv([make_env])
    batch_size = 2048
    set_global_seeds(seed)

    # policy = "MlpLnLstmPolicy"
    policy = "MlpPolicy"
    model = PPO2(
        policy=policy,
        env=env,
        n_steps=batch_size,
        nminibatches=1,
        lam=0.95,
        gamma=0.99,
        noptepochs=10,
        ent_coef=0.0,
        learning_rate=3e-4,
        cliprange=0.2,
        verbose=1,
    )

    if save and save_interval > 0:
        callback = init_save_callback(logdir, batch_size, save_interval)
    else:
        callback = None

    # Optionally load before or save after training
    if load is not None:
        model.load_parameters(load)
    model.learn(total_timesteps=num_timesteps, callback=callback)
    if save:
        model.save(logdir + "/model")

    return model, env


def main():

    # Parse command line args
    parser = arg_parser()
    parser.add_argument("-ns", "--num-timesteps", type=str, default="1e6")
    parser.add_argument("-ld", "--logdir", type=str, default="logs")
    parser.add_argument("-l", "--load", type=str, default=None)
    parser.add_argument("-s", "--save", action="store_true")
    parser.add_argument("-si", "--save-interval", type=float, default=5e4)
    parser.add_argument("-sd", "--seed", type=int, default=-1)
    parser.add_argument(
        "-o", "--output-formats", nargs="*", default=["stdout", "log", "csv"]
    )
    args = parser.parse_args()

    # Set default seed
    if args.seed == -1:
        seed = np.random.randint(1, 1000)
        print("Seed is", seed)
    else:
        seed = args.seed

    logdir = "{}/{}/seed-{}".format(args.logdir, args.num_timesteps, str(seed))
    logger.configure(logdir, args.output_formats)

    # Round save interval to a multiple of 2048
    save_interval = int(np.ceil(args.save_interval / 2048)) if args.save else 0

    # Run training script (+ loading/saving)
    model, env = train(
        num_timesteps=int(float(args.num_timesteps)),
        logdir=logdir,
        save=args.save,
        save_interval=save_interval,
        load=args.load,
        seed=seed,
    )

    env.close()


if __name__ == "__main__":
    main()
