# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Misc.

# <headingcell level=3>

# Pythonesque stuff

# <codecell>

#!/usr/bin/env python
from random import *
from pylab import *
from mpl_toolkits.mplot3d import axes3d, Axes3D
from scipy.integrate import dblquad

def non_scalar_vectorize(func, input_shape, output_shape):
    """Return a featurized version of func, where func takes a potentially matricial argument and returns a potentially matricial answer.

    These functions can not be naively vectorized by numpy's vectorize.
 
    With vfunc = non_scalar_vectorize( func, (2,), (10,1) ),
    
    func([p,s]) will return a 2D matrix of shape (10,1).

    func([[p1,s1],...,[pn,sn]]) will return a 3D matrix of shape (n,10,1).

    And so on.
    """
    def vectorized_func(arg):
        #print 'Vectorized : arg = '+str(arg)
        nbinputs = prod(arg.shape)/prod(input_shape)
        if nbinputs == 1:
            return func(arg)
        outer_shape = arg.shape[:len(arg.shape)-len(input_shape)]
        outer_shape = outer_shape if outer_shape else (1,)
        arg = arg.reshape((nbinputs,)+input_shape)
        answers=[]
        for input_matrix in arg:
            answers.append(func(input_matrix))
        return array(answers).reshape(outer_shape+output_shape)
    return vectorized_func

def zip_stack(*args):
    """Given matrices of same shape, return a matrix whose elements are tuples from the arguments (i.e. with one more dimension).

    zip_stacking three matrices of shape (n,p) will yeld a matrix of shape (n,p,3)
    """
    shape = args[0].shape
    nargs = len(args)
    args = [m.reshape(-1) for m in args]
    return array(zip(*args)).reshape(shape+(nargs,))
#zip_stack(array([[1,2,3],[4,5,6]]),rand(2,3))

# <headingcell level=2>

# Inverted Pendulum-specific code

# <codecell>

RANDOM_RUN_LENGTH=5000
EXPERT_RUN_LENGTH=3000
TRANS_WIDTH=6
ACTION_SPACE=[0,1,2]
GAMMA=0.9 #Discout factor
LAMBDA=0.1 #Regularization coeff for LSTDQ

# <codecell>

def inverted_pendulum_single_psi( state ):
    position,speed=state
    answer = zeros((10,1))
    index = 0
    answer[index] = 1.
    index+=1
    for i in linspace(-pi/4,pi/4,3):
        for j in linspace(-1,1,3):
            answer[index] = exp(-(pow(position-i,2) +
                                  pow(speed-j,2))/2.)
            index+=1
    #print "psi stops ar index "+str(index)
    return answer

inverted_pendulum_psi = non_scalar_vectorize( inverted_pendulum_single_psi,(2,), (10,1) )

#[inverted_pendulum_psi(rand(2)).shape,
# inverted_pendulum_psi(rand(2,2)).shape,
# inverted_pendulum_psi(rand(3,5,2)).shape]

# <codecell>

def inverted_pendulum_single_phi(state_action):
    position, speed, action = state_action
    answer = zeros((30,1))
    index = action*10
    answer[ index:index+10 ] = inverted_pendulum_single_psi( [position, speed] )
    return answer

inverted_pendulum_phi = non_scalar_vectorize(inverted_pendulum_single_phi, (3,), (30,1))

#[inverted_pendulum_phi(rand(3)).shape,
# inverted_pendulum_phi(rand(3,3)).shape,
# inverted_pendulum_phi(rand(4,5,3)).shape]

# <codecell>

def inverted_pendulum_V(omega):
    policy = greedy_policy( omega, inverted_pendulum_phi, ACTION_SPACE )
    def V(pos,speed):
        actions = policy(zip_stack(pos,speed))
        Phi=inverted_pendulum_phi(zip_stack(pos,speed,actions))
        return squeeze(dot(omega.transpose(),Phi))
    return V

# <codecell>

def inverted_pendulum_next_state(state, action):
    position,speed = state
    noise = rand()*20.-10.
    control = None
    if action == 0:
        control = -50 + noise;
    elif action == 1:
        control = 0 + noise;
    else: #action==2
        control = 50 + noise;
    g = 9.8;
    m = 2.0;
    M = 8.0;
    l = 0.50;
    alpha = 1./(m+M);
    step = 0.1;
    acceleration = (g*sin(position) - 
                    alpha*m*l*pow(speed,2)*sin(2*position)/2. - 
                    alpha*cos(position)*control) / (4.*l/3. - alpha*m*l*pow(cos(position),2))
    next_position = position +speed*step;
    next_speed = speed + acceleration*step;
    return array([next_position,next_speed])

def inverted_pendulum_single_reward( sas ):
    position,speed = sas[-2:]
    #print "position is "+str(position)
    if abs(position)>pi/2.:
    #    print "-1"
        return -1.
    #print "0"
    return 0.

inverted_pendulum_vreward = non_scalar_vectorize( inverted_pendulum_single_reward, (5,),(1,1) )
inverted_pendulum_reward = lambda sas:squeeze(inverted_pendulum_vreward(sas))

def inverted_pendulum_uniform_initial_state():
    return array(uniform(low=-pi/2, high=pi/2, size=2))

def inverted_pendulum_nice_initial_state():
    return array(uniform(low=-0.1, high=0.1, size=2))

def inverted_pendulum_trace( policy,run_length=RANDOM_RUN_LENGTH,
                             initial_state=inverted_pendulum_uniform_initial_state,
                             reward = inverted_pendulum_reward):
    data = zeros((run_length, TRANS_WIDTH))
    state = initial_state()
    for i,void in enumerate( data ):
        action = policy( state )
        new_state = inverted_pendulum_next_state( state, action )
        r = reward( hstack([state,action,new_state]) )
        data[i,:] = hstack([state,action,new_state,[r]])
        if r == 0.:
            state = new_state
        else: #Pendulum has fallen
            state = initial_state()
    return data

def inverted_pendulum_random_trace(reward=inverted_pendulum_reward,
                                    initial_state=inverted_pendulum_nice_initial_state):
    pi = lambda s: choice(ACTION_SPACE)
    return inverted_pendulum_trace( pi,reward=reward, initial_state=initial_state)

def inverted_pendulum_expert_trace( reward ):
    data = inverted_pendulum_random_trace(reward=reward)
    policy,omega = lspi( data, s_dim=2,a_dim=1, A=ACTION_SPACE, phi=inverted_pendulum_phi, phi_dim=30, iterations_max=10 )
    inverted_pendulum_plot(inverted_pendulum_V(omega))
    two_args_pol = lambda p,s:squeeze(policy(zip_stack(p,s)))
    inverted_pendulum_plot(two_args_pol,contour_levels=3)
    return inverted_pendulum_trace( policy,run_length=EXPERT_RUN_LENGTH ),policy,omega

# <codecell>

def inverted_pendulum_plot( f, draw_contour=True, contour_levels=50, draw_surface=False ):
    '''Display a surface plot of function f over the state space'''
    pos = linspace(-pi,pi,30)
    speed = linspace(-pi,pi,30)
    pos,speed = meshgrid(pos,speed)
    Z = f(pos,speed)
    fig = figure()
    if draw_surface:
        ax=Axes3D(fig)
        ax.plot_surface(pos,speed,Z)
    if draw_contour:
        contourf(pos,speed,Z,levels=linspace(min(Z.reshape(-1)),max(Z.reshape(-1)),contour_levels+1))
        colorbar()
    #show()
def inverted_pendulum_plot_policy( policy ):
    two_args_pol = lambda p,s:squeeze(policy(zip_stack(p,s)))
    inverted_pendulum_plot(two_args_pol,contour_levels=3)

def inverted_pendulum_plot_SAReward(reward,policy):
    X = linspace(-pi,pi,30)
    Y = X
    X,Y = meshgrid(X,Y)
    XY = zip_stack(X,Y)
    XYA = zip_stack(X,Y,squeeze(policy(XY)))
    Z = squeeze(reward(XYA))
    contourf(X,Y,Z,levels=linspace(min(Z.reshape(-1)),max(Z.reshape(-1)),51))
    colorbar()

    
def inverted_pendulum_plot_SReward(reward,policy):
    X = linspace(-pi,pi,30)
    Y = X
    X,Y = meshgrid(X,Y)
    XY = zip_stack(X,Y)
    XYA = zip_stack(X,Y,squeeze(policy(XY)))
    Z = squeeze(reward(XYA))
    contourf(X,Y,Z,levels=linspace(min(Z.reshape(-1)),max(Z.reshape(-1)),51))
    colorbar()

#test_omega=zeros((30,1)
#test_omega[5]=1.
#inverted_pendulum_plot(inverted_pendulum_V(test_omega))
#pol = greedy_policy(test_omega,inverted_pendulum_phi,ACTION_SPACE)
#inverted_pendulum_plot_policy(policy_good)

# <headingcell level=2>

# Reinforcement Learning Code

# <codecell>

def argmax( set, func ):
     return max( zip( set, map(func,set) ), key=lambda x:x[1] )[0]

def greedy_policy( omega, phi, A ): 
    def policy( *args ):
        state_actions = [hstack(args+(a,)) for a in A]
        q_value = lambda sa: float(dot(omega.transpose(),phi(sa)))
        best_action = argmax( state_actions, q_value )[-1] #FIXME6: does not work for multi dimensional actions
        return best_action
    vpolicy = non_scalar_vectorize( policy, (2,), (1,1) )
    return lambda state: vpolicy(state).reshape(state.shape[:-1]+(1,))

#test_omega=zeros((30,1))
#test_omega[1]=1.
#pol = greedy_policy( test_omega, inverted_pendulum_phi, ACTION_SPACE )
#[pol(rand(2)),pol(rand(3,2)).shape,pol(rand(3,3,2)).shape]

# <codecell>

def lstdq(phi_sa, phi_sa_dash, rewards, phi_dim=1):
    #print "shapes of phi de sa, phi de sprim a prim, rewards"+str(phi_sa.shape)+str(phi_sa_dash.shape)+str(rewards.shape)
    A = zeros((phi_dim,phi_dim))
    b = zeros((phi_dim,1))
    for phi_t,phi_t_dash,reward in zip(phi_sa,phi_sa_dash,rewards):
        A = A + dot( phi_t,
                     (phi_t - GAMMA*phi_t_dash).transpose())
        b = b + phi_t*reward
    return dot(inv(A + LAMBDA*identity( phi_dim )),b)

def lspi( data, s_dim=1, a_dim=1, A = [0], phi=None, phi_dim=1, epsilon=0.01, iterations_max=30,
          plot_func=None):
    nb_iterations=0
    sa = data[:,0:s_dim+a_dim]
    phi_sa = phi(sa)
    s_dash = data[:,s_dim+a_dim:s_dim+a_dim+s_dim]
    rewards = data[:,s_dim+a_dim+s_dim]
    omega = zeros(( phi_dim, 1 ))
    #omega = genfromtxt("../Code/InvertedPendulum/omega_E.mat").reshape(30,1)
    diff = float("inf")
    cont = True
    policy = greedy_policy( omega, phi, A )
    while cont:
        if plot_func:
            plot_func(omega)
        sa_dash = hstack([s_dash,policy(s_dash)])
        phi_sa_dash = phi(sa_dash)
        omega_dash = lstdq(phi_sa, phi_sa_dash, rewards, phi_dim=phi_dim)
        diff = norm( omega_dash-omega )
        omega = omega_dash
        policy = greedy_policy( omega, phi, A )
        nb_iterations+=1
        print "LSPI, iter :"+str(nb_iterations)+", diff : "+str(diff)
        if nb_iterations > iterations_max or diff < epsilon:
            cont = False
    sa_dash = hstack([s_dash,policy(s_dash)])
    phi_sa_dash = phi(sa_dash)
    omega = lstdq(phi_sa, phi_sa_dash, rewards, phi_dim=phi_dim) #Omega is the Qvalue of pi, but pi is not the greedy policy w.r.t. omega
    return policy,omega

# <headingcell level=2>

# Experiment 1 Code

# <codecell>

psi=inverted_pendulum_psi
phi=inverted_pendulum_phi
true_reward=lambda s,p:inverted_pendulum_reward(zip_stack(zeros(s.shape),zeros(s.shape),zeros(s.shape),s,p))
inverted_pendulum_plot(true_reward)
#Defining the expert policy
data_random = inverted_pendulum_random_trace()
data_expert,policy,omega = inverted_pendulum_expert_trace(inverted_pendulum_reward)

# <codecell>

#Defining the expert's stationary distribution
#On peut jouer avec la longueur d'un run et le nombre de runs
trajs = vstack([inverted_pendulum_trace(policy, run_length=60) for i in range(0,20)])
plot(trajs[:,0],trajs[:,1],ls='',marker='o')
axis([-10,10,-10,10])

# <codecell>

#On génère des runs de longueur suffisante, on vire les quelques premiers échantillons, et on prend un échantillon sur quelques uns par la suite
trajs = [inverted_pendulum_trace(policy, run_length=1000) for i in range(0,2)]
sampled_trajs = [t[100:999:10,:] for t in trajs]
expert_distrib_samples = vstack([t[:,-3:-1] for t in sampled_trajs])
plot(expert_distrib_samples[:,0],expert_distrib_samples[:,1],ls='',marker='o')
#axis([-10,10,-10,10])

# <codecell>

from sklearn import mixture
rho_E = mixture.GMM(covariance_type='full')
rho_E.fit(expert_distrib_samples)

pos = linspace(-0.3,0.3,30)
speed = linspace(-2,2,30)
pos,speed = meshgrid(pos,speed)
#g.score(zip_stack(pos,speed).reshape((30*30,2))).shape
Z = exp(rho_E.score(zip_stack(pos,speed).reshape((30*30,2)))).reshape((30,30))
#Z = two_arg_gaussian(pos,speed)
fig = figure()
contourf(pos,speed,Z,50)
colorbar()
scatter(expert_distrib_samples[:,0],expert_distrib_samples[:,1],s=1)
rho_E.sample()

# <codecell>

#Données : 
traj = inverted_pendulum_trace(policy, run_length=300)
s=traj[:,:2]
a=traj[:,2]
#Classification
from sklearn import svm
clf = svm.SVC(C=1000., probability=True)
clf.fit(s, a)
clf_predict= lambda state : clf.predict(squeeze(state))
vpredict = non_scalar_vectorize( clf_predict, (2,), (1,1) )
pi_c = lambda state: vpredict(state).reshape(state.shape[:-1]+(1,))
clf_score = lambda sa : squeeze(clf.predict_proba(squeeze(sa[:2])))[sa[-1]]
vscore = non_scalar_vectorize( clf_score,(3,),(1,1) )
q = lambda sa: vscore(sa).reshape(sa.shape[:-1])
#Plots de la politique de l'expert, des données fournies par l'expert, de la politique du classifieur
inverted_pendulum_plot_policy(policy)
scatter(traj[:,0],traj[:,1],c=traj[:,2])
inverted_pendulum_plot_policy(pi_c)
scatter(traj[:,0],traj[:,1],c=traj[:,2])
##Plots de Q et de la fonction de score du classifieur et évaluation de la politique du classifieur
#phi=inverted_pendulum_phi
Q = lambda sa: squeeze(dot(omega.transpose(),phi(sa)))
Q_0 = lambda p,s:Q(zip_stack(p,s,0*ones(p.shape)))
Q_1 = lambda p,s:Q(zip_stack(p,s,1*ones(p.shape)))
Q_2 = lambda p,s:Q(zip_stack(p,s,2*ones(p.shape)))
q_0 = lambda p,s:q(zip_stack(p,s,0*ones(p.shape)))
q_1 = lambda p,s:q(zip_stack(p,s,1*ones(p.shape)))
q_2 = lambda p,s:q(zip_stack(p,s,2*ones(p.shape)))
inverted_pendulum_plot(Q_0)
inverted_pendulum_plot(Q_1)
inverted_pendulum_plot(Q_2)
inverted_pendulum_plot(q_0)
inverted_pendulum_plot(q_1)
inverted_pendulum_plot(q_2)

# <codecell>

#Données pour la regression
column_shape = (len(traj),1)
s = traj[:,0:2]
a = traj[:,2].reshape(column_shape)
sa = traj[:,0:3]
s_dash = traj[:,3:5]
a_dash = pi_c(s_dash).reshape(column_shape)
sa_dash = hstack([s_dash,a_dash])
hat_r = (q(sa)-GAMMA*q(sa_dash)).reshape(column_shape)
r_min = min(hat_r)-1.*ones(column_shape)
#Plot des samples hat_r Pour chacune des 3 actions
sar = hstack([sa,hat_r])
for action in ACTION_SPACE:
    sr = array([l for l in sar if l[2]==action])
    axis([-pi,pi,-pi,pi])
    scatter(sr[:,0],sr[:,1],s=20,c=sr[:,3], marker = 'o', cmap = cm.jet );
    colorbar()
    figure()
##Avec l'heuristique : 
regression_input_matrices = [hstack([s,action*ones(column_shape)]) for action in ACTION_SPACE] 
def add_output_column( reg_mat ):
    actions = reg_mat[:,-1].reshape(column_shape)
    hat_r_bool_table = array(actions==a)
    r_min_bool_table = array(hat_r_bool_table==False) #"not hat_r_bool_table" does not work as I expected
    output_column = hat_r_bool_table*hat_r+r_min_bool_table*r_min
    return hstack([reg_mat,output_column])
regression_matrix = vstack(map(add_output_column,regression_input_matrices))
#On plotte les mêmes données que juste précedemment, mais avec l'heuristique en prime
for action in ACTION_SPACE:
    sr = array([l for l in regression_matrix if l[2]==action])
    axis([-pi,pi,-pi,pi])
    scatter(sr[:,0],sr[:,1],s=20,c=sr[:,3], marker = 'o', cmap = cm.jet );
    colorbar()
    figure()

# <codecell>

#Régression
from sklearn.svm import SVR
y = regression_matrix[:,-1]
X = regression_matrix[:,:-1]
reg = SVR(C=1.0, epsilon=0.2)
reg.fit(X, y)
CSI_reward = lambda sas:reg.predict(sas[:3])[0]
vCSI_reward = non_scalar_vectorize( CSI_reward, (5,),(1,1) )
#On plotte les rewards en fonction de l'action
for action in ACTION_SPACE:
    sr = array([l for l in regression_matrix if l[2]==action])
    R = lambda p,s: squeeze( vCSI_reward(zip_stack(p,s,action*ones(p.shape),p,s)))
    pos = linspace(-pi,pi,30)
    speed = linspace(-pi,pi,30)
    pos,speed = meshgrid(pos,speed)
    Z = R(pos,speed)
    figure()
    contourf(pos,speed,Z,50)
    scatter(sr[:,0],sr[:,1],s=20,c=sr[:,3], marker = 'o', )#cmap = cm.jet );
    clim(vmin=min(Z.reshape(-1)),vmax=max(Z.reshape(-1)))
    colorbar()
def mean_reward(s,p):
    actions = [a*ones(s.shape) for a in ACTION_SPACE]
    matrices = [zip_stack(s,p,a,s,p) for a in actions]
    return mean(array([squeeze(vCSI_reward(m)) for m in matrices]), axis=0)
inverted_pendulum_plot(mean_reward)

# <codecell>

#Evaluation de l'IRL
data_CSI,policy_CSI,omega_CSI = inverted_pendulum_expert_trace(CSI_reward)

# <codecell>

#Critères de performance pour l'imitation
GAMMAS = array([pow(GAMMA,n) for n in range(0,70)])
def imitation_performance(policy):
    trajs = [inverted_pendulum_trace(policy, run_length=70) for i in range(0,100)]
    values = [sum(traj[:,5]*GAMMAS) for traj in  trajs]
    return mean(values)

#imitation_performance_policy(policy)

# <codecell>

#Critère de performance pour l'IRL
trajs_IRL = [inverted_pendulum_trace(policy_CSI, run_length=70, initial_state=lambda:rho_E.sample().reshape((2,))) for i in range(0,100)]
rewards_IRL = [vCSI_reward(traj[:,:5]) for traj in trajs_IRL]
value_IRL = mean([sum(r*GAMMAS) for r in rewards_IRL]) #V^*_{\hat R_C}
def IRL_performance(policy):
    trajs = [inverted_pendulum_trace(policy, run_length=70) for i in range(0,100)]
    rewards = [vCSI_reward(traj[:,:5]) for traj in trajs]
    value = mean([sum(r*GAMMAS) for r in rewards])
    return value_IRL-value

# <codecell>

print "Critere uniforme, expert :\t"+str(imitation_performance(policy))
print "Critere uniforme, classifieur :\t"+str(imitation_performance(pi_c))
print "Critere uniforme, IRL :\t"+str(imitation_performance(policy_CSI))

# <codecell>

print "Critere de la borne, expert :\t"+str(IRL_performance(policy))
print "Critere de la borne, classifieur :\t"+str(IRL_performance(pi_c))
print "Critere de la borne, IRL :\t"+str(IRL_performance(policy_CSI))

# <codecell>

print "Abcisse possible, nb samples :\t"+str(traj.shape[0])
#sampled_pi_E = policy(rho_E.sample(7000))
#sampled_pi_C = pi_c(rho_E.sample(7000))
print "Abcisse possible, epsilon_C :\t"+str(sum(sampled_pi_C != sampled_pi_E)/7000.)
#Epsilon R est techniquement calculable, mais pas franchement simple.
#print "Abcisse possible, epsilon_R"
