import numpy as np
from numpy.core.numeric import allclose
import pandas as pd
from scipy.linalg import toeplitz, block_diag
from scipy.spatial.distance import cdist
from itertools import product
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge, LinearRegression, Lasso
from sklearn.model_selection import cross_validate, GroupKFold, KFold
from sklearn.cluster import KMeans

from sklearn.base import BaseEstimator
from sklearn.utils.validation import check_X_y, check_array, check_is_fitted


class RelaxedLasso(BaseEstimator):
  def __init__(self, 
               lambd=1.0, 
               fit_intercept=True, 
              #  lasso_type='relaxed',
              #  refit_type='full',
               normalize='deprecated', 
               precompute=False, 
               copy_X=True, 
               max_iter=1000, 
               tol=0.0001, 
               warm_start=False, 
               positive=False, 
               random_state=None, 
               selection='cyclic'):
    (self.lambd, 
     self.fit_intercept,
    #  self.lasso_type,
    #  self.refit_type,
     self.normalize,
     self.precompute,
     self.copy_X,
     self.max_iter,
     self.tol,
     self.warm_start,
     self.positive,
     self.random_state,
     self.selection) = (lambd, 
                        fit_intercept,
                        # lasso_type,
                        # refit_type,
                        normalize,
                        precompute,
                        copy_X,
                        max_iter,
                        tol,
                        warm_start,
                        positive,
                        random_state,
                        selection)
    
    self.lassom = Lasso(alpha=lambd, 
                        fit_intercept=fit_intercept,
                        normalize=normalize,
                        precompute=precompute,
                        copy_X=copy_X,
                        max_iter=max_iter,
                        tol=tol,
                        warm_start=warm_start,
                        positive=positive,
                        random_state=random_state,
                        selection=selection)
    
    self.linm = LinearRegression(fit_intercept=fit_intercept,
                                 copy_X=copy_X,
                                 positive=positive)
    

  def fit(self, X, lasso_y, lin_y=None,
          sample_weight=None,
          check_input=True):

    if lin_y is None:
      lin_y = lasso_y.copy()

    self.lassom.fit(X, lasso_y,
                    sample_weight=sample_weight,
                    check_input=check_input)
    
    self.E_ = E = np.where(self.lassom.coef_ != 0)[0]
    self.XE_ = XE = X[:,E]

    self.linm.fit(XE, lin_y,
                  sample_weight=sample_weight)

    # self.linm.fit(X, lin_y,
    #               sample_weight=sample_weight)
    
    return self
    

  def predict(self, X):
    XE = X[:,self.E_]
    return self.linm.predict(XE)

    # return self.linm.predict(X)
