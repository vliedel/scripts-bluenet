
import numpy as np


# beta: current estimate of parameters
# jacobian: derivative of function, with beta as parameters
# residuals: ri = yi - f(xi, beta)
def step(beta, jacobian, residuals):
#    print("shapes: beta=", np.shape(beta), "jacobian=", np.shape(jacobian), "residuals", np.shape(residuals))
#    print("beta:", beta)
#    print("jacobian:", jacobian)
#    print("residuals:", residuals)
    jacobianT = jacobian.transpose()

#    print("inverse of:", jacobianT.dot(jacobian))
    try:
        nextBeta = beta - np.linalg.inv(jacobianT.dot(jacobian)).dot(jacobianT).dot(residuals)
    except np.linalg.LinAlgError:
        nextBeta = beta
    return nextBeta

def gauss_newton(func, beta0, jacobian, numSteps):
    """


    Parameters
    ----------
    func : callable
        Function in the form of: y_i - f(x_i, beta), with beta as function input.
    beta0 : ndarray
        The starting parameters estimate for the minimization.
    jacobian : callable
        Derivative of func with respect to beta: dfunc / dbeta
    numSteps : int
        Number of iterations.

    Returns
    -------
    beta : ndarray
        The solution (or the result of the last iteration for an unsuccessful
        call).
    """

    beta = beta0
#    print("beta: ", beta)
    for i in range(0, numSteps):
        r = func(beta)
        j = np.array(jacobian(beta)).transpose()
        beta = step(beta, j, r)
#        print("beta: ", beta)
    return beta