import numpy as np
import torch

from utils.nnet import from_gpu
from utils.eval import compute_accuracy

class Optimiser():
    def __init__(self, args):
        self.lrate_sgd = args.lrate_sgd 
        self.lrate_hebb = args.lrate_hebb
        self.hebb_normaliser = args.hebb_normaliser 
        self.perform_sgd = args.perform_sgd 
        self.perform_hebb = args.perform_hebb 
        self.gating = args.gating
        self.losstype = args.loss_funct
        print(self.perform_sgd)


    def step(self,model,x_in, r_target):
        
        if self.perform_sgd==True:
            self.sgd_update(model,x_in,r_target)            
        if self.perform_hebb==True:
            if self.gating=='SLA':                
                self.sla_update(model,x_in)
            elif self.gating=='GHA':
                self.gha_update(model,x_in)        


    def sgd_update(self,model,x_in,r_target):
        '''
        performs sgd update 
        '''
        y_ = model(x_in)
        # compute loss 
        loss = self.loss_funct(r_target, y_)
        # get gradients 
        loss.backward()
        # update weights 
        with torch.no_grad():
            for theta in model.parameters():
                if theta.requires_grad:
                    theta -= theta.grad*self.lrate_sgd
            model.zero_grad()


    def sla_update(self,model,x_in):
        '''
        performs update with subspace learning algorithm
        '''
        # x_in = torch.t(x_in) # 27x1
        x_in = x_in.reshape(27,1)
        with torch.no_grad():
            Y = torch.t(model.W_h) @ x_in 
            Y = Y.reshape(-1)
            x_in = x_in.reshape(-1)
            model.W_h += torch.t((torch.outer(Y,x_in) - torch.outer(Y,model.W_h @ Y) / self.hebb_normaliser) * self.lrate_hebb)
            model.zero_grad()


    def gha_update(self, model, x_in):
        '''
        performs update with generalised hebbian algorithm
        '''
        x_in = torch.t(x_in) # 27x1
        with torch.no_grad():
            Y = torch.t(model.W_h) @ x_in            
            model.W_h += torch.t((torch.outer(Y,x_in) - (torch.tril(torch.outer(Y,Y)) @ torch.t(model.W_h)) / self.hebb_normaliser) * self.lrate_hebb)
            model.zero_grad()


    def loss_funct(self,reward,y_hat):
        '''
        loss function to use.
        either negative reward or MSE on the model outputs.
        (or mse between logistic model output and true labels (or subject responses))
        '''
        if self.losstype=='reward':
            # minimise -1*reward 
            loss = -1*torch.t(torch.sigmoid(y_hat)) @ reward
        elif self.losstype=='mse':
            loss = torch.mean(torch.pow(reward-y_hat,2)) 
        elif self.losstype=='sigmoidmse':
            loss = torch.mean(torch.pow(reward-torch.sigmoid(y_hat),2)) 
        return loss



def train_model(args,model,optim,data, logger):
    '''
    trains neural network model
    '''

    # send data to gpu
    x_train = torch.from_numpy(data['x_train']).float().to(args.device)
    y_train = torch.from_numpy(data['y_train']).float().to(args.device)

    # test: create test sets 
    x_a = torch.from_numpy(data['x_task_a']).float().to(args.device)
    r_a = torch.from_numpy(data['y_task_a']).float().to(args.device)

    x_b = torch.from_numpy(data['x_task_b']).float().to(args.device)
    r_b = torch.from_numpy(data['y_task_b']).float().to(args.device)

    x_both = torch.from_numpy(np.concatenate((data['x_task_a'],data['x_task_b']),axis=0)).float().to(args.device)
    r_both = torch.from_numpy(np.concatenate((data['y_task_a'],data['y_task_b']),axis=0)).float().to(args.device)

    # log state of initialised model
    logger.log_init(model)
    logger.log_patterns(model,x_both)

    # loop over data and apply optimiser
    idces = np.arange(len(x_train))
    for ii, x,y in zip(idces,x_train,y_train):
        optim.step(model,x,y)
        if ii%args.log_interval==0:
            
            logger.log_step(model,optim,x_a,x_b,x_both,r_a,r_b,r_both)
            if args.verbose:
                print('step {}, loss: task a {:.4f}, task b {:.4f} | acc: task a {:.4f}, task b {:.4f}'.format(str(ii), logger.losses_1st[-1],logger.losses_2nd[-1], logger.acc_1st[-1],logger.acc_2nd[-1]))
                print('... n_a: {:d} n_b: {:d}'.format(logger.n_only_a[-1],logger.n_only_b[-1]))
    
    logger.log_patterns(model,x_both)
    print('done')
  