import numpy as np

class Bayes():

    '''
    Class with methods for bayesian analysis of different kinds of signals. The methods currently
    include prior and likelihood functions for ISGWB analysis, sky-pixel/radiometer type analysis
    and a power spectra based spherical harmonic analysis.
    '''

    def __init__(self):
        '''
        Init for intializing
        '''
        self.r12 = np.conj(self.r1)*self.r2
        self.r13 = np.conj(self.r1)*self.r3
        self.r21 = np.conj(self.r2)*self.r1
        self.r23 = np.conj(self.r2)*self.r3
        self.r31 = np.conj(self.r3)*self.r1
        self.r32 = np.conj(self.r3)*self.r2
        self.rbar = np.stack((self.r1, self.r2, self.r3), axis=2)

        ## create a data correlation matrix
        self.rmat = np.zeros((self.rbar.shape[0], self.rbar.shape[1], self.rbar.shape[2], self.rbar.shape[2]), dtype='complex')

        for ii in range(self.rbar.shape[0]):
            for jj in range(self.rbar.shape[1]):
                self.rmat[ii, jj, :, :] = np.tensordot(np.conj(self.rbar[ii, jj, :]), self.rbar[ii, jj, :], axes=0 )



    def instr_prior(self, theta):


        '''
        Prior function for only instrumental noise

        Parameters
        -----------

        theta   : float
            A list or numpy array containing samples from a unit cube.

        Returns
        ---------

        theta   :   float
            theta with each element rescaled. The elements are  interpreted as alpha, omega_ref, Np and Na

        '''


        # Unpack: Theta is defined in the unit cube
        log_Np, log_Na = theta

        # Transform to actual priors
        log_Np = -5*log_Np - 39
        log_Na = -5*log_Na - 46

        return (log_Np, log_Na)


    def isgwb_prior(self, theta):


        '''
        Prior function for an isotropic stochastic backgound analysis.

        Parameters
        -----------

        theta   : float
            A list or numpy array containing samples from a unit cube.

        Returns
        ---------

        theta   :   float
            theta with each element rescaled. The elements are  interpreted as alpha, omega_ref, Np and Na

        '''


        # Unpack: Theta is defined in the unit cube
        log_Np, log_Na, alpha, log_omega0 = theta
        # Transform to actual priors
        alpha       =  10*alpha-5
        log_omega0  = -10*log_omega0 - 4
        log_Np      = -5*log_Np - 39
        log_Na      = -5*log_Na - 46
        self.theta_prior = (alpha, log_omega0, log_Np, log_Na)
        return (log_Np, log_Na, alpha, log_omega0)

    def primo_prior(self, theta):
        
        # log_Np, log_Na, nHat = theta
        ## Setting wHat as a parameter too
        # log_Np, log_Na, nHat, wHat = theta
        log_Np, log_Na, wHat, nHat = theta
        wHat = 1*wHat + 0.55
        nHat = 1*nHat + 0.22 
        log_Np = -5*log_Np - 39
        log_Na = -5*log_Na - 46
        
        # return (log_Np, log_Na, nHat, wHat)
        return (log_Np, log_Na, wHat, nHat)
        # return (log_Np, log_Na, nHat)
        
    def sph_prior(self, theta):

        '''
        Prior for a power spectra based spherical harmonic anisotropic analysis
        Parameters
        -----------
        theta   : float
            A list or numpy array containing samples from a unit cube.
        Returns
        ---------
        theta   :   float
            theta with each element rescaled. The elements are  interpreted as alpha, omega_ref for each of the harmonics, Np and Na. The first element is always alpha and the last two are always Np and Na
        '''

        # The first two are the priors on the position and acc noise terms.
        log_Np = -4*theta[0] - 39
        log_Na = -4*theta[1] - 46

        # Prior on alpha, and omega_0
        alpha = 8*theta[2] - 4
        log_omega0  = -6*theta[3] - 5

        # The rest of the priors define the blm parameter space
        blm_theta = []

        ## counter for the rest of theta
        cnt = 4

        for lval in range(1, self.params['lmax'] + 1):
            for mval in range(lval + 1):

                if mval == 0:
                    blm_theta.append(6*theta[cnt] - 3)
                    cnt = cnt + 1
                else:
                    ## prior on amplitude, phase
                    blm_theta.append(3* theta[cnt])
                    blm_theta.append(2*np.pi*theta[cnt+1] - np.pi)
                    cnt = cnt + 2

        # rm these three lines later.
        # blm_theta.append(theta[4])
        # blm_theta.append(2*np.pi*theta[5] - np.pi)

        theta = [log_Np, log_Na, alpha, log_omega0] + blm_theta


        return theta

    def isgwb_only_prior(self, theta):


        '''
        Prior function for an isotropic stochastic backgound analysis.

        Parameters
        -----------

        theta   : float
            A list or numpy array containing samples from a unit cube.

        Returns
        ---------

        theta   :   float
            theta with each element rescaled. The elements are  interpreted as alpha, omega_ref

        '''

        # Unpack: Theta is defined in the unit cube
        alpha, log_omega0  = theta

        # Transform to actual priors
        alpha       = 10*alpha-5
        log_omega0  = -10*log_omega0 - 4

        return (alpha, log_omega0)

    def isgwb_only_log_likelihood(self, theta):

        '''
        Calculate likelihood for an isotropic stochastic background analysis.
        Parameters
        -----------
        theta   : float
            A list or numpy array containing rescaled samples from the unit cube. The elementes are interpreted as samples for alpha, omega_ref, Np and Na respectively.
        Returns
        ---------
        Loglike   :   float
            The log-likelihood value at the sampled point in the parameter space
        '''

        # unpack priors
        alpha, log_omega0  = theta

        ## Signal PSD
        H0 = 2.2*10**(-18)
        Omegaf = 10**(log_omega0)*(self.fdata/self.params['fref'])**alpha

        # Spectrum of the SGWB
        Sgw = Omegaf*(3/(4*self.fdata**3))*(H0/np.pi)**2

        ## The noise spectrum of the GW signal. Written down here as a full
        ## covariance matrix axross all the channels.
        ## change axis order to make taking an inverse easier
        cov_sgwb = Sgw[:, None, None, None]*np.moveaxis(self.response_mat, [-2, -1, -3], [0, 1, 2])

        ## take inverse and determinant
        inv_cov, det_cov = bespoke_inv(cov_sgwb)

        logL = -np.einsum('ijkl,ijkl', inv_cov, self.rmat) - np.einsum('ij->', np.log(np.pi * self.params['seglen'] * np.abs(det_cov)))

        loglike = np.real(logL)

        return loglike


    def instr_log_likelihood(self, theta):

        '''
        Calculate likelihood for only instrumental noise
        Parameters
        -----------
        theta   : float
            A list or numpy array containing rescaled samples from the unit cube. The elementes are interpreted as samples for  Np and Na respectively.
        Returns
        ---------
        Loglike   :   float
            The log-likelihood value at the sampled point in the parameter space
        '''


        # unpack priors
        log_Np, log_Na  = theta

        Np, Na =  10**(log_Np), 10**(log_Na)

        # Modelled Noise PSD
        cov_noise = self.instr_noise_spectrum(self.fdata,self.f0, Np, Na)


        ## repeat C_Noise to have the same time-dimension as everything else
        cov_noise = np.repeat(cov_noise[:, :, :, np.newaxis], self.tsegmid.size, axis=3)

        ## change axis order to make taking an inverse easier
        cov_mat = np.moveaxis(cov_noise, [-2, -1], [0, 1])

        ## take inverse and determinant
        inv_cov, det_cov = bespoke_inv(cov_mat)

        logL = -np.einsum('ijkl,ijkl', inv_cov, self.rmat) - np.einsum('ij->', np.log(np.pi * self.params['seglen'] * np.abs(det_cov)))


        loglike = np.real(logL)

        return loglike


    def isgwb_log_likelihood(self, theta):

        '''
        Calculate likelihood for an isotropic stochastic background analysis.
        Parameters
        -----------
        theta   : float
            A list or numpy array containing rescaled samples from the unit cube. The elementes are interpreted as samples for alpha, omega_ref, Np and Na respectively.
        Returns
        ---------
        Loglike   :   float
            The log-likelihood value at the sampled point in the parameter space
        '''

        # unpack priors
        log_Np, log_Na, alpha, log_omega0 = theta

        Np, Na =  10**(log_Np), 10**(log_Na)

        # Modelled Noise PSD
        cov_noise = self.instr_noise_spectrum(self.fdata,self.f0, Np, Na)

        ## repeat C_Noise to have the same time-dimension as everything else (noise power spectrum)
        cov_noise = np.repeat(cov_noise[:, :, :, np.newaxis], self.tsegmid.size, axis=3)
        
        ## Signal PSD
        H0 = 2.2*10**(-18)
        Omegaf = 10**(log_omega0)*(self.fdata/self.params['fref'])**alpha

        # Spectrum of the SGWB
        Sgw = Omegaf*(3/(4*self.fdata**3))*(H0/np.pi)**2

        ## The noise spectrum of the GW signal. Written down here as a full
        ## covariance matrix axross all the channels.
        cov_sgwb = Sgw[None, None, :, None]*self.response_mat

        cov_mat = cov_sgwb + cov_noise

        ## change axis order to make taking an inverse easier
        cov_mat = np.moveaxis(cov_mat, [-2, -1], [0, 1])

        ## take inverse and determinant
        inv_cov, det_cov = bespoke_inv(cov_mat)

        logL = -np.einsum('ijkl,ijkl', inv_cov, self.rmat) - np.einsum('ij->', np.log(np.pi * self.params['seglen'] * np.abs(det_cov)))


        loglike = np.real(logL)

        return loglike

    
    
    def sph_log_likelihood(self, theta):

        '''
        Calculate likelihood for a power-spectra based spherical harmonic analysis.
        Parameters
        -----------
        theta   : float
            A list or numpy array containing rescaled samples from the unit cube. The elements are  interpreted as alpha, omega_ref for each of the harmonics, Np and Na. The first element is always alpha and the last two are always Np and Na.
        Returns
        ---------
        Loglike   :   float
            The log-likelihood value at the sampled point in the parameter space
        '''

        # unpack priors
        log_Np, log_Na, alpha, log_omega0  = theta[0],theta[1], theta[2], theta[3]

        Np, Na =  10**(log_Np), 10**(log_Na)

        # Modelled Noise PSD
        cov_noise = self.instr_noise_spectrum(self.fdata, self.f0, Np, Na)

        ## repeat C_Noise to have the same time-dimension as everything else
        cov_noise = np.repeat(cov_noise[:, :, :, np.newaxis], self.tsegmid.size, axis=3)

        ## Signal PSD
        H0 = 2.2*10**(-18)
        Omegaf = 10**(log_omega0)*(self.fdata/self.params['fref'])**alpha

        # Spectrum of the SGWB
        Sgw = Omegaf*(3/(4*self.fdata**3))*(H0/np.pi)**2

        ## rm this line later
        # blm_theta  = np.append([0.0], theta[4:])

        blm_theta  = theta[4:]

        ## Convert the blm parameter space values to alm values.
        blm_vals = self.blm_params_2_blms(blm_theta)
        alm_vals = self.blm_2_alm(blm_vals)

        ## normalize
        alm_vals = alm_vals/(alm_vals[0] * np.sqrt(4*np.pi))

        summ_response_mat = np.einsum('ijklm,m', self.response_mat, alm_vals)

        ## The noise spectrum of the GW signal. Written down here as a full
        ## covariance matrix axross all the channels.
        cov_sgwb = Sgw[None, None, :, None]*summ_response_mat

        cov_mat = cov_sgwb + cov_noise

        ## change axis order to make taking an inverse easier
        cov_mat = np.moveaxis(cov_mat, [-2, -1], [0, 1])

        ## take inverse and determinant
        inv_cov, det_cov = bespoke_inv(cov_mat)

        logL = -np.einsum('ijkl,ijkl', inv_cov, self.rmat) - np.einsum('ij->', np.log(np.pi * self.params['seglen'] * np.abs(det_cov)))

        loglike = np.real(logL)

        return loglike


    def primo_log_likelihood(self, theta):
        
        ## Setting wHat as a parameter too
        # log_Np, log_Na, nHat, wHat = theta
        log_Np, log_Na, wHat, nHat = theta
        # log_Np, log_Na, nHat = theta
        
        ## Comment this if wHat is a parameter too
        # wHat = self.inj['wHat']
        ##
        
        Np, Na = 10**(log_Np), 10**(log_Na)
        
        # Modelled Noise PSD
        cov_noise = self.instr_noise_spectrum(self.fdata,self.f0, Np, Na)

        ## repeat C_Noise to have the same time-dimension as everything else
        cov_noise = np.repeat(cov_noise[:, :, :, np.newaxis], self.tsegmid.size, axis=3)

        ## Signal PSD
        H0 = 2.2*10**(-18)
        g_bbn = 10.75
        gs_bbn = 10.75
        g_eq = 3.3626
        gs_eq = 3.9091
        del_R = 2.25*10**-9
        z_bbn = 5.9*10**9 - 1
        kcmb = 0.05

        gamma = ((2.3*10**4))**-1 * (g_bbn/g_eq) * (gs_eq/gs_bbn)**1.3333
        
        A1 = (del_R**2)*gamma/24
        A2 = (2*np.pi*self.fdata/H0) * (1 / (gamma**0.5 * (1 + z_bbn)))
        A3 = (2*np.pi*self.fdata/H0) * (0.72/150.)
        alpha_hat = 2 * (3 * wHat - 1) / (3 * wHat + 1)

        Omegaf = self.inj['rts'] * (A1 * A2**alpha_hat * A3**nHat)
        
        # Spectrum of the SGWB
        Sgw = Omegaf*(3/(4*self.fdata**3))*(H0/np.pi)**2
        
        ## The noise spectrum of the GW signal. Written down here as a full
        ## covariance matrix axross all the channels.
        cov_sgwb = Sgw[None, None, :, None]*self.response_mat

        cov_mat = cov_sgwb + cov_noise

        ## change axis order to make taking an inverse easier
        cov_mat = np.moveaxis(cov_mat, [-2, -1], [0, 1])

        ## take inverse and determinant
        inv_cov, det_cov = bespoke_inv(cov_mat)

        logL = -np.sum(inv_cov*self.rmat) - np.sum(np.log(np.pi * self.params['seglen'] * np.abs(det_cov)))

        loglike = np.real(logL)
        
        return loglike

def bespoke_inv(A):

    """
    compute inverse without division by det; ...xv3xc3 input, or array of matrices assumed
    Credit to Eelco Hoogendoorn at stackexchange for this piece of wizardy. This is > 3 times
    faster than numpy's det and inv methods used in a fully vectorized way as of numpy 1.19.1
    https://stackoverflow.com/questions/21828202/fast-inverse-and-transpose-matrix-in-python
    """


    AI = np.empty_like(A)

    for i in range(3):
        AI[...,i,:] = np.cross(A[...,i-2,:], A[...,i-1,:])

    det = np.einsum('...i,...i->...', AI, A).mean(axis=-1)

    inv_T =  AI / det[...,None,None]

    # inverse by swapping the inverse transpose
    return np.swapaxes(inv_T, -1,-2), det
