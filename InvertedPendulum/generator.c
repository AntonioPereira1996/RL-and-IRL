#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <math.h>
#include "InvertedPendulum.h"
#include <gsl/gsl_matrix.h>
#include "utils.h"
#define NUMBER_OF_WALKS (500)
#define MAX_WALK_LENGTH (3000)

int main( void ){
  srand(time(NULL)+getpid()); rand(); rand();rand();
  for( unsigned int i = 0 ; i < NUMBER_OF_WALKS ; i++ ){
    double state_p;//position
    double state_v;//vitesse
    iv_init( &state_p, &state_v );
    int eoe = 1;
    for( unsigned int j = 0 ; j < MAX_WALK_LENGTH && eoe == 1 ; 
	 j++ ){
      double next_state_p;
      double next_state_v;
      double reward;
      unsigned int action = random_int( LEFT, RIGHT );
      iv_step( state_p, state_v, action, 
	       &next_state_p, &next_state_v, &reward, &eoe );
      if( j == MAX_WALK_LENGTH - 1 ){
	eoe = 0;
      }
      printf("%lf %lf %d %lf %lf %lf %d\n",
	     state_p, state_v, action, 
	     next_state_p, next_state_v, reward, eoe );
      state_p = next_state_p;
      state_v = next_state_v;
    }
  }
  return 0;
}
