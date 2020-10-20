#!/usr/bin/env python3
"""This is an example to train a task with PPO algorithm.

It creates Metaworld environmetns. And uses a PPO with 10M
steps.

"""

import click
import gym
import numpy as np
import pickle
import tensorflow as tf

from metaworld.envs.mujoco.env_dict import ALL_V1_ENVIRONMENTS, ALL_V2_ENVIRONMENTS

from garage import wrap_experiment
from garage.envs import GymEnv, normalize
from garage.experiment import LocalTFRunner
from garage.experiment.deterministic import set_seed
from garage.tf.algos import PPO
from garage.tf.baselines import GaussianMLPBaseline
from garage.tf.policies import GaussianMLPPolicy

from garage.sampler import LocalSampler

@click.command()
@click.option('--env-name', type=str, default="pick-place-v2")
@click.option('--seed', type=int, default=np.random.randint(0, 1000))
@click.option('--entropy', type=float, default=0.01)
@click.option('--use_softplus_entropy', type=bool, default=False)
@click.option('--extra_tags', type=str, default="none")
@wrap_experiment(name_parameters='all', snapshot_mode='gap', snapshot_gap=5)
def ppo_metaworld_reach_pick(ctxt=None, env_name=None, tag="add_obj_orientation", extra_tags="", entropy=0.05, stop_entropy_gradient=True, use_softplus_entropy=False, seed=1,):
    """Train PPO with Metaworld environments.

    Args:
        ctxt (garage.experiment.ExperimentContext): The experiment
            configuration used by LocalRunner to create the snapshotter.
        seed (int): Used to seed the random number generator to produce
            determinism.

    """
    set_seed(seed)
    special = {'push-v1' : "push", 'reach-v1' : "reach", "pick-place-v1": "pick_place"}
    not_in_mw = 'the env_name specified is not a metaworld environment'
    assert env_name in ALL_V2_ENVIRONMENTS or env_name in ALL_V1_ENVIRONMENTS, not_in_mw

    if env_name in ALL_V2_ENVIRONMENTS:
        env_cls = ALL_V2_ENVIRONMENTS[env_name]
    else:
        env_cls = ALL_V1_ENVIRONMENTS[env_name]

    env = env_cls()
    env._partially_observable = False
    env._freeze_rand_vec = False
    env._set_task_called = True
    env.reset()
    env._freeze_rand_vec = True
    max_path_length = env.max_path_length
    env = normalize(GymEnv(env), normalize_reward=True)
    with LocalTFRunner(snapshot_config=ctxt) as runner:
        policy = GaussianMLPPolicy(
            env_spec=env.spec,
            hidden_sizes=(64, 64),
            hidden_nonlinearity=tf.nn.tanh,
            output_nonlinearity=None,
        )

        baseline = GaussianMLPBaseline(
            env_spec=env.spec,
            hidden_sizes=(32, 32),
            use_trust_region=True,
        )

        # NOTE: make sure when setting entropy_method to 'max', set
        # center_adv to False and turn off policy gradient. See
        # tf.algos.NPO for detailed documentation.
        algo = PPO(
            env_spec=env.spec,
            policy=policy,
            baseline=baseline,
            max_episode_length=max_path_length,
            discount=0.99,
            gae_lambda=0.95,
            lr_clip_range=0.2,
            optimizer_args=dict(
                batch_size=32,
                max_episode_length=10,
            ),
            stop_entropy_gradient=stop_entropy_gradient,
            entropy_method='max',
            policy_ent_coeff=entropy,
            center_adv=False,
            use_softplus_entropy=use_softplus_entropy,
        )

        runner.setup(algo, env, sampler_cls=LocalSampler)
        runner.train(n_epochs=int(5000000/(max_path_length*100)), batch_size=(max_path_length*100), plot=False)


ppo_metaworld_reach()
