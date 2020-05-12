from sklearn.linear_model import LinearRegression, LogisticRegression
from imblearn.over_sampling import SMOTE, SVMSMOTE, ADASYN, RandomOverSampler

# Importing data
explored = pd.read_csv('data/explored.csv')
unexplored = pd.read_csv('data/unexplored.csv')


def build_x_y():
  """Create balanced classes by oversampling."""
  X = explored.drop(columns=['latitude', 'longitude', 'mp_score'])
  X_pred = unexplored.copy()

  # For now, running classification models instead of regression.
  y = explored.mp_score > 0
  y = y.map(lambda x: 1 if x else 0)

  # Oversampling the imbalanced class.
  X, y = SVMSMOTE().fit_resample(X, y)
  
  return X, y, X_pred


def run_lin_reg():
  """Run a simple linear regression."""
  X, y, X_pred = build_x_y()
  reg = LinearRegression().fit(X, y)
  print('Linear regression fit score: ' + str(reg.score(X, y)) + '\n')
  y_pred = reg.predict(X_pred.drop(columns=['latitude', 'longitude', 'mp_score']))
  X_pred['predicted_score'] = y_pred
  X_pred.height *= 1000
  X_pred = X_pred.sort_values(by='predicted_score', ascending=False)[['latitude', 'longitude', 'height', 'mp_score', 'predicted_score']]
  X_pred.to_csv('data/predictions/linear_reg_predictions.csv', header=True, index=False)
  
  print('Top 30 results from linear regression prediction.')
  print('A higher score is better!\n')
  print(X_pred[:30].to_string(index=False))



# Logistic regression
# xgboost gradient boost for regression
# nn regression
# random forest