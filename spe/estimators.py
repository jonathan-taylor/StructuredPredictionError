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

from .data_generator import DataGen
from .relaxed_lasso import RelaxedLasso

class RandEstimator(object):
  # def __init__(self, 
  #              model):
  #   self.model = model


  def estimate_risk(self,
                    X,
                    y,
                    nboot=100,
                    model,
                    kwargs={}):

    return self._estimate(X=X,
                          y=y,
                          nboot=nboot, 
                          model=model,
                          est_risk=True,
                          **kwargs)

  def estimate_mse(self,
                   X,
                   y,
                   nboot=100,
                   model,
                   kwargs={}):

    return self._estimate(X=X,
                          y=y,
                          nboot=nboot, 
                          model=model, 
                          est_risk=False,
                          **kwargs)


class CBIsotropic(RandEstimator):

  def _estimate(self,
                X,
                y,
                sigma=None,
                nboot=100,
                alpha=1.,
                model=LinearRegression(),
                est_risk=True):

    X = X
    y = y
    (n, p) = X.shape

    if sigma is None:
      model.fit(X, y)
      yhat = model.predict(X)
      sigma = np.sqrt(((y - yhat)**2).mean()) # not sure how to get df for general models...

    boot_ests = np.zeros(nboot)

    for b in np.arange(nboot):
      eps = sigma * np.random.randn(n)
      w = y + eps*np.sqrt(alpha)
      wp = y - eps/np.sqrt(alpha)

      model.fit(X, w)
      yhat = model.predict(X)

      boot_ests[b] = np.sum((wp - yhat)**2) - np.sum(eps**2)/alpha

    return (boot_ests.mean() - (n*sigma**2)*est_risk) #/ n


class CB(RandEstimator):

  def _estimate(self,
                X, 
                y, 
                Chol_t=None, 
                Chol_eps=None,
                Theta=None,
                nboot=100,
                model=LinearRegression(),
                est_risk=True):

    X = X
    y = y
    (n, p) = X.shape

    if Chol_eps is None:
      Chol_eps = np.eye(n)
      Sigma_eps = Chol_eps
    else:
      Sigma_eps = Chol_eps @ Chol_eps.T
    
    Prec_eps = np.linalg.inv(Sigma_eps)

    if Chol_t is None:
      Chol_t = np.eye(n)
      Sigma_t = np.eye(n)
    else:
      Sigma_t = Chol_t @ Chol_t.T

    proj_t_eps = Sigma_t @ Prec_eps

    if Theta is None:
      Theta = np.eye(n)
    Sigma_t_Theta = Sigma_t @ Theta

    boot_ests = np.zeros(nboot)

    for b in np.arange(nboot):
      eps = Chol_eps @ np.random.randn(n)
      w = y + eps
      regress_t_eps = proj_t_eps @ eps
      wp = y - regress_t_eps

      model.fit(X, w)
      yhat = model.predict(X)

      boot_ests[b] = np.sum((wp - yhat)**2) - (regress_t_eps.T.dot(Theta @ regress_t_eps)).sum()

    return (boot_ests.mean() - np.diag(Sigma_t_Theta).sum()*est_risk) #/ n


# class BlurLinear(RandEstimator):
#   def __init__(self, 
#                X, 
#                y, 
#                Chol_t, 
#                Chol_eps):

#     super.__init__(LinearRegression, 
#                    X, 
#                    y, 
#                    Chol_t)

#     self.Chol_eps = Chol_eps
#     self.Sigma_eps = Chol_eps @ Chol_eps.T
#     self.Prec_eps = np.linalg.inv(self.Sigma_eps)
#     self.proj_t_eps = self.Sigma_t @ self.Prec_eps
#     self.P = X @ np.linalg.inv(X.T @ X) @ X.T

#   def _estimate(self,
#                 X, 
#                 y, 
#                 Chol_t=None, 
#                 Chol_eps=None,
#                 Theta=None,
#                 nboot=100,
#                 model=LinearRegression(),
#                 est_risk=True):

#     X = X
#     y = y
#     (n, p) = X.shape

#     if Chol_eps is None:
#       Chol_eps = np.eye(n)
#       Sigma_eps = Chol_eps
#     else:
#       Sigma_eps = Chol_eps @ Chol_eps.T
    
#     Prec_eps = np.linalg.inv(Sigma_eps)

#     if Chol_t is None:
#       Chol_t = np.eye(n)
#       Sigma_t = np.eye(n)
#     else:
#       Sigma_t = Chol_t @ Chol_t.T

#     proj_t_eps = Sigma_t @ Prec_eps

#     if Theta is None:
#       Theta = np.eye(n)
#     Sigma_t_Theta = Sigma_t @ Theta

#     boot_ests = np.zeros(nboot)

#     for b in np.arange(nboot):
#       eps = self.Chol_t @ np.random.randn(self.n)
#       w = y + eps
#       regress_t_eps = self.proj_t_eps @ eps
#       wp = y - regress_t_eps

#       model.fit(X, w)
#       yhat = model.predict(X)

#       boot_ests[b] = np.sum((wp - yhat)**2) - np.sum(regress_t_eps**2) - np.sum((self.P @ eps)**2)

#     return (boot_ests.mean() - np.diag(Sigma_t_Theta).sum()*est_risk) / self.n


class KFoldCV(object):

  def _estimate(self, 
                model, 
                X, 
                y, 
                k=5):

    self.kfcv_res = kfcv_res = cross_validate(model, X, y, 
                                              scoring='neg_mean_squared_error', 
                                              cv=KFold(k, shuffle=True), 
                                              error_score='raise')
    return -np.mean(kfcv_res['test_score'])


class KMeansCV(object):

  def _estimate(self, 
                model, 
                X, 
                y, 
                k=5):

    groups = KMeans(n_clusters=k).fit(X).labels_
    self.spcv_res = spcv_res = cross_validate(model, 
                                              X, 
                                              y, 
                                              scoring='neg_mean_squared_error', 
                                              cv=GroupKFold(k), 
                                              groups=groups)

    return -np.mean(spcv_res['test_score'])


class TestSetEstimator(object):

  def _estimate(self, 
                model, 
                X, 
                y,
                y_test,
                Chol_t=None, 
                Theta=None,
                est_risk=True):

    (n, p) = X.shape

    if Chol_t is None:
      Chol_t = np.eye(n)

    Sigma_t = Chol_t @ Chol_t.T

    if Theta is None:
      Theta = np.eye(n)

    Sigma_t_Theta = Sigma_t @ Theta

    model.fit(X, y)
    preds = model.predict(X)
    sse = np.sum((y_test - preds)**2)

    return (sse - np.diag(Sigma_t_Theta).sum()*est_risk) #/ n


