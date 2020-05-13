import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.linear_model import LinearRegression, LogisticRegression
from imblearn.over_sampling import SMOTE, SVMSMOTE, ADASYN, RandomOverSampler

# Importing data
explored = pd.read_csv('data/explored.csv')
unexplored = pd.read_csv('data/unexplored.csv')


def build_x_y(prob=0.9):
  """Create balanced classes by oversampling."""
  X_pred = unexplored.copy()  # to be used to make predictions

  X = explored.drop(columns=['latitude', 'longitude', 'mp_score'])
  mask = np.random.rand(len(X)) < prob
  X_train = X[mask]
  X_test = X[~mask]

  # For now, running classification models instead of regression.
  y = explored.mp_score > 0
  y = y.map(lambda x: 1 if x else 0)
  y_train = y[mask]
  y_test = y[~mask]

  # Oversampling the imbalanced training data.
  X_train, y_train = RandomOverSampler().fit_resample(X_train, y_train)

  return X_train, y_train, X_test, y_test, X_pred


def run_lin_reg():
  """Run a simple linear regression."""
  X_train, y_train, X_test, y_test, X_pred = build_x_y()
  reg = LinearRegression().fit(X_train, y_train)
  print('Linear regression fit score: ' + str(reg.score(X_test, y_test)) + '\n')
  y_pred = reg.predict(X_pred.drop(columns=['latitude', 'longitude', 'mp_score']))
  X_pred['predicted_score'] = y_pred
  X_pred.height *= 1000
  X_pred = X_pred.sort_values(by='predicted_score', ascending=False)[['latitude', 'longitude', 'height', 'mp_score', 'predicted_score']]
  X_pred.to_csv('data/predictions/linear_reg_predictions.csv', header=True, index=False)

  print('Top 20 results from linear regression prediction.')
  print('A higher score is better!\n')
  print(X_pred[:20].to_string(index=False))


def run_log_reg():
  """Run a simple logistic classification."""
  X_train, y_train, X_test, y_test, X_pred = build_x_y()
  reg = LogisticRegression(max_iter=200).fit(X_train, y_train)
  print('Logistic regression fit score: ' + str(reg.score(X_test, y_test)) + '\n')
  
  # Use predict_proba() to get probabilities of hittng a class, not classes themselves.
  # On the otherhand, predict() uses a cutoff at 0.5 to make a choice.
  y_pred = reg.predict_proba(X_pred.drop(columns=['latitude', 'longitude', 'mp_score']))
  y_pred = y_pred[:, 1:]
  
  X_pred['predicted_score'] = y_pred
  X_pred.height *= 1000
  X_pred = X_pred.sort_values(by='predicted_score', ascending=False)[['latitude', 'longitude', 'height', 'mp_score', 'predicted_score']]
  X_pred.to_csv('data/predictions/logistic_reg_predictions.csv', header=True, index=False)
  
  print('Top 20 results from logistic regression prediction.')
  print('A higher score is better!\n')
  print(X_pred[:20].to_string(index=False))

def run_xgb():
  X_train, y_train, X_test, y_test, X_pred = build_x_y()
  # dmatrix = xgb.DMatrix(data=X_train, label=y_train)
  # can also use XGBClassifier
  reg = xgb.XGBRegressor(objective ='reg:squarederror', colsample_bytree = 0.3, learning_rate = 0.1,
              max_depth = 5, alpha = 10, n_estimators = 10)
  reg.fit(X_train, y_train)
  
  y_pred = reg.predict(X_pred.drop(columns=['latitude', 'longitude', 'mp_score']))
  X_pred['predicted_score'] = y_pred
  X_pred.height *= 1000
  X_pred = X_pred.sort_values(by='predicted_score', ascending=False)[['latitude', 'longitude', 'height', 'mp_score', 'predicted_score']]
  X_pred.to_csv('data/predictions/xgb_predictions.csv', header=True, index=False)

  print('Top 20 results from xgb prediction.')
  print('A higher score is better!\n')
  print(X_pred[:20].to_string(index=False))




# nn regression
# random forest


if __name__ == '__main__':
  run_lin_reg()
  run_log_reg()
  run_xgb()