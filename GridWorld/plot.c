#include <gsl/gsl_matrix.h>
#include "GridWorld.h"
#include "simulator.h"
#include "utils.h"
#include "LSPI.h"
#include "abbeel2004apprenticeship.h"
#include "LSTDmu.h"
#include "criteria.h"
#include "RL_Globals.h"
#include "IRL_Globals.h"
#define D_FILE_NAME "Samples.dat"
#define TRANS_WIDTH 7
#define ACTION_FILE "actions.mat"

unsigned int g_iK = (GRID_HEIGHT*GRID_WIDTH*4); /* dim(\phi) */
unsigned int g_iP = (GRID_HEIGHT*GRID_WIDTH); /* dim(\psi) */

gsl_matrix* phi( gsl_matrix* sa ){
  gsl_matrix* answer = gsl_matrix_calloc( g_iK, 1 );
  unsigned int x = (unsigned int)gsl_matrix_get( sa, 0, 0 );
  unsigned int y = (unsigned int)gsl_matrix_get( sa, 0, 1 );
  unsigned int a = (unsigned int)gsl_matrix_get( sa, 0, 2 );
  unsigned int index = (y-1)*GRID_WIDTH*4 + (x-1)*4 + a-1;
  gsl_matrix_set( answer, index, 0, 1.0 );
  return answer;
}

gsl_matrix* psi( gsl_matrix* s ){
  gsl_matrix* answer = gsl_matrix_calloc( g_iP, 1 );
  unsigned int x = (unsigned int)gsl_matrix_get( s, 0, 0 );
  unsigned int y = (unsigned int)gsl_matrix_get( s, 0, 1 );
  unsigned int index = (y-1)*GRID_WIDTH + (x-1);
  gsl_matrix_set( answer, index, 0, 1.0 );
  return answer;
}

gsl_matrix* initial_state( void ){
  gsl_matrix* answer = gsl_matrix_alloc( 1, 2 );
  gsl_matrix_set( answer, 0, 0, 1.0 );
  gsl_matrix_set( answer, 0, 1, 1.0 );
  return answer;
}

unsigned int g_iS = 2;
unsigned int g_iA = 1;
unsigned int g_iIt_max_lspi = 20;
gsl_matrix* (*g_fPhi)(gsl_matrix*) = &phi;
gsl_matrix* g_mOmega = NULL;
double g_dLambda_lstdQ = 0.1;
double g_dGamma_lstdq =  0.9;
double g_dEpsilon_lspi = 0.1;
double g_dLambda_lstdmu = 0.1;
double g_dGamma_anirl = 0.9;
double g_dEpsilon_anirl = 0.1;
unsigned int g_iIt_max_anirl = 40;
gsl_matrix* g_mActions = NULL; 
gsl_matrix* (*g_fPsi)(gsl_matrix*) = &psi;
gsl_matrix* (*g_fSimulator)(int) = &gridworld_simulator;
gsl_matrix* (*g_fS_0)(void) = &initial_state;

int main( void ){
  gsl_matrix* D = file2matrix( D_FILE_NAME, TRANS_WIDTH );
  g_mActions = file2matrix( ACTION_FILE, g_iA );
  gsl_matrix* omega_0 = gsl_matrix_calloc( g_iK, 1 );
  gsl_matrix* omega_expert = lspi( D, omega_0 );
  g_mOmega_E = omega_expert;
  expert_just_set();
  /* Courbe A : différences entre les mesures pour MC */
  unsigned int M = 500;
  g_iNb_samples = D->size1;
  g_mOmega =  omega_expert;
  gsl_matrix* D_expert = gridworld_simulator( M );
  gsl_matrix* omega_imitation =
    proj_mc_lspi_ANIRL( D_expert, D, M );
  gsl_matrix_free( omega_imitation );
  gsl_matrix_free( D_expert );
  /*Courbes B & C : Performance de MC et LSTDmu*/
  M = 501; //To differentiate from above when greping.
  //See the Makefile
  int m_exp[] = {1,10,30,50,75,100,200};
  for( int i=0; i<7 ; i++ ){
    g_iNb_samples = 0;
    g_mOmega =  omega_expert;
    gsl_matrix* D_expert = gridworld_simulator( m_exp[i] );
    unsigned int nb_samples_exp = g_iNb_samples;
    gsl_matrix* omega_lstd = 
      proj_lstd_lspi_ANIRL( D_expert, D_expert );
    gsl_matrix_free( omega_lstd );
    printf("B %d %lf %lf %lf %lf\n", nb_samples_exp, 
	   g_dBest_t, g_dBest_error, 
	   g_dBest_true_error, g_dBest_diff );
    gsl_matrix* omega_imitation =
      proj_mc_lspi_ANIRL( D_expert, D, M );
    gsl_matrix_free( omega_imitation );
    gsl_matrix_free( D_expert );
    printf("C %d %lf %lf %lf %lf\n", nb_samples_exp, 
	   g_dBest_t, g_dBest_error, 
	   g_dBest_true_error, g_dBest_diff );
  }
  return 0;
}
