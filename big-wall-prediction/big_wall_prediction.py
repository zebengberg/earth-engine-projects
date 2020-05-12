from sklearn.linear_model import LinearRegression, LogisticRegression
from imblearn.over_sampling import SMOTE, SVMSMOTE, ADASYN, RandomOverSampler

# Importing data
explored = pd.read_csv('data/explored.csv')
unexplored = pd.read_csv('data/unexplored.csv')

X = explored.drop(columns=['latitude', 'longitude', 'mp_score']).values
X_pred = unexplored.drop(columns=['latitude', 'longitude', 'mp_score']).values

# For now, running classification models instead of regression.
y = explored.mp_score > 0
y = y.map(lambda x: 1 if x else 0)
y = y.values

# Oversampling the imbalanced class.
X, y = SVMSMOTE().fit_resample(X, y)



# Linear regression
reg = LinearRegression().fit(X, y)
y_pred = reg.predict(X_pred)


# Logistic regression
reg = LogisticRegression(max_iter=200).fit(X, y)
y_pred = reg.predict(X_pred)


# xgboost gradient boost for regression



# nn regression




# random forest