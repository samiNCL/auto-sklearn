import numpy as np

from ConfigSpace.configuration_space import ConfigurationSpace
from ConfigSpace.hyperparameters import UniformFloatHyperparameter, \
    UniformIntegerHyperparameter, UnParametrizedHyperparameter, Constant, \
    CategoricalHyperparameter

from autosklearn.pipeline.components.base import (
    AutoSklearnRegressionAlgorithm,
    IterativeComponent,
)
from autosklearn.pipeline.constants import SPARSE, DENSE, UNSIGNED_DATA, PREDICTIONS
from autosklearn.util.common import check_for_bool


class MLPRegressor(
    IterativeComponent,
    AutoSklearnRegressionAlgorithm
):
    def __init__(self, hidden_layer_depth, num_nodes_per_layer, activation, alpha,
                 learning_rate_init, early_stopping, solver, batch_size,
                 # n_iter_no_change, validation_fraction=None, tol,
                 shuffle, beta_1, beta_2, epsilon,
                 random_state=None, verbose=0):
        self.hidden_layer_depth = hidden_layer_depth
        self.num_nodes_per_layer = num_nodes_per_layer
        self.max_iter = self.get_max_iter()
        self.activation = activation
        self.alpha = alpha
        self.learning_rate_init = learning_rate_init
        self.early_stopping = early_stopping
        # self.n_iter_no_change = n_iter_no_change
        # self.validation_fraction = validation_fraction
        # self.tol = tol
        self.solver = solver
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.beta_1 = beta_1
        self.beta_2 = beta_2
        self.epsilon = epsilon
        self.beta_1 = beta_1

        self.random_state = random_state
        self.verbose = verbose
        self.estimator = None
        self.fully_fit_ = False

    @staticmethod
    def get_max_iter():
        return 512

    def get_current_iter(self):
        return self.estimator.max_iter

    def iterative_fit(self, X, y, n_iter=2, refit=False):
        """
        Set n_iter=2 for the same reason as for SGD
        """
        from sklearn.neural_network import MLPRegressor
        import sklearn.preprocessing
        n_iter = max(n_iter, 2)

        if refit:
            self.estimator = None
            self.scaler = None

        if self.estimator is None:
            self.fully_fit_ = False

            self.hidden_layer_depth = int(self.hidden_layer_depth)
            self.num_nodes_per_layer = int(self.num_nodes_per_layer)
            self.hidden_layer_sizes = tuple(self.num_nodes_per_layer
                                            for i in range(self.hidden_layer_depth))
            self.activation = str(self.activation)
            self.alpha = float(self.alpha)
            self.learning_rate_init = float(self.learning_rate_init)
            self.early_stopping = str(self.early_stopping)
            if self.early_stopping == "off":
                self.early_stopping_val = False
                # self.validation_fraction = 0.0
                # Turn early stopping completely off
                self.n_iter_no_change = self.max_iter
                self.tol = 0
            else:
                raise ValueError("Can't use early_stopping (set to %s)" % self.early_stopping)
                # self.early_stopping_val = True
                # self.validation_fraction = 0.0
                # self.n_iter_no_change = self.max_iter
                # self.tol = 0
            self.solver = self.solver

            try:
                self.batch_size = int(self.batch_size)
            except ValueError:
                self.batch_size = str(self.batch_size)

            self.shuffle = check_for_bool(self.shuffle)
            self.beta_1 = float(self.beta_1)
            self.beta_2 = float(self.beta_2)
            self.epsilon = float(self.epsilon)
            self.beta_1 = float(self.beta_1)

            self.max_iter = int(self.max_iter)
            self.verbose = int(self.verbose)

            n_iter = int(np.ceil(n_iter))

            # initial fit of only increment trees
            self.estimator = MLPRegressor(
                hidden_layer_sizes=self.hidden_layer_sizes,
                activation=self.activation,
                solver=self.solver,
                alpha=self.alpha,
                batch_size=self.batch_size,
                learning_rate_init=self.learning_rate_init,
                max_iter=n_iter,
                shuffle=self.shuffle,
                random_state=self.random_state,
                verbose=self.verbose,
                warm_start=True,
                early_stopping=self.early_stopping_val,
                # validation_fraction=self.validation_fraction,
                n_iter_no_change=self.n_iter_no_change,
                tol=self.tol,
                beta_1=self.beta_2,
                beta_2=self.beta_1,
                epsilon=self.epsilon,
                # We do not use these, see comments below in search space
                # momentum=self.momentum,
                # nesterovs_momentum=self.nesterovs_momentum,
                # power_t=self.power_t,
                # learning_rate=self.learning_rate,
                # max_fun=self.max_fun
            )
            self.scaler = sklearn.preprocessing.StandardScaler(copy=True)
            self.scaler.fit(y.reshape((-1, 1)))
            Y_scaled = self.scaler.transform(y.reshape((-1, 1))).ravel()
            iter_left = None
        else:
            Y_scaled = self.scaler.transform(y.reshape((-1, 1))).ravel()
            iter_left = min(self.max_iter - self.estimator.n_iter_, n_iter)
            self.estimator.max_iter = iter_left

        self.estimator.fit(X, Y_scaled)
        if self.estimator.n_iter_ >= self.max_iter:
            self.fully_fit_ = True
        return self

    def configuration_fully_fitted(self):
        if self.estimator is None:
            return False
        elif not hasattr(self, 'fully_fit_'):
            return False
        else:
            return self.fully_fit_

    def predict(self, X):
        if self.estimator is None:
            raise NotImplementedError
        Y_pred = self.estimator.predict(X)
        return self.scaler.inverse_transform(Y_pred)

    @staticmethod
    def get_properties(dataset_properties=None):
        return {'shortname': 'MLP',
                'name': 'Multilayer Percepton',
                'handles_regression': True,
                'handles_classification': False,
                'handles_multiclass': False,
                'handles_multilabel': False,
                'handles_multioutput': False,
                'is_deterministic': True,
                'input': (DENSE, SPARSE, UNSIGNED_DATA),
                'output': (PREDICTIONS,)}

    @staticmethod
    def get_hyperparameter_search_space(dataset_properties=None):
        cs = ConfigurationSpace()
        hidden_layer_depth = UniformIntegerHyperparameter(name="hidden_layer_depth",
                                                          lower=1, upper=3, default_value=1)
        num_nodes_per_layer = UniformIntegerHyperparameter(name="num_nodes_per_layer",
                                                           lower=16, upper=264, default_value=32,
                                                           log=True)
        activation = CategoricalHyperparameter(name="activation", choices=['tanh', 'logistic'],
                                               default_value='tanh')
        alpha = UniformFloatHyperparameter(name="alpha", lower=1e-5, upper=1e-0, default_value=1e-4,
                                           log=True)

        learning_rate_init = UniformFloatHyperparameter(name="learning_rate_init",
                                                        lower=1e-4, upper=0.5, default_value=1e-3,
                                                        log=True)
        # *Note*: If "early_stopping" is set to true, we can't use warm_starting. This
        # is fixed w/ scikit-learn>=0.24 and we can make this a categorical with off/train/valid
        early_stopping = Constant(name="early_stopping", value="off")

        # We don't need these since we turn off early_stopping
        # n_iter_no_change = Constant(name="n_iter_no_change", value=10)
        # validation_fraction = Constant(name="validation_fraction", value=0.0)
        # tol = UnParametrizedHyperparameter(name="tol", value=1e-4)

        # Constants
        solver = Constant(name="solver", value='adam')

        # Relying on sklearn defaults for now
        batch_size = UnParametrizedHyperparameter(name="batch_size", value="auto")
        shuffle = UnParametrizedHyperparameter(name="shuffle", value="True")
        beta_1 = UnParametrizedHyperparameter(name="beta_1", value=0.9)
        beta_2 = UnParametrizedHyperparameter(name="beta_2", value=0.999)
        epsilon = UnParametrizedHyperparameter(name="epsilon", value=1e-8)

        # Not used
        # solver=["sgd", "lbfgs"] --> not used to keep searchspace simpler
        # learning_rate --> only used when using solver=sgd
        # power_t --> only used when using solver=sgd & learning_rate=invscaling
        # momentum --> only used when solver=sgd
        # nesterovs_momentum --> only used when solver=sgd
        # max_fun --> only used when solver=lbfgs
        # activation=["identity", "logistic"] --> not useful for classification

        cs.add_hyperparameters([hidden_layer_depth, num_nodes_per_layer,
                                activation, alpha,
                                learning_rate_init, early_stopping,
                                # n_iter_no_change, validation_fraction, tol,
                                solver, batch_size, shuffle,
                                beta_1, beta_2, epsilon])

        # We don't need these since we turn off early_stopping
        # validation_fraction_cond = InCondition(validation_fraction, early_stopping, ["valid"])
        # cs.add_conditions([validation_fraction_cond])

        return cs