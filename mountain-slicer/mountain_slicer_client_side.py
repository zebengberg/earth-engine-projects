import pandas as pd
import matplotlib.pyplot as plt
from sklearn import linear_model


# Importing data calculated by server.
df = pd.read_csv('navajo.csv')
df = df.drop(['system:index', '.geo'], axis=1)
df = df[df['elevation'] > 2000]

# Running linear regression.
reg = linear_model.LinearRegression()
x = df[['elevation']]
y = df['perimeter']
reg.fit(x, y)
y_pred = reg.predict(x)

# Plotting results.
plt.plot(x, y, 'ro', x, y_pred, ms=1)
plt.show()

# Another plot.
plt.plot('elevation', 'area', data=df)
