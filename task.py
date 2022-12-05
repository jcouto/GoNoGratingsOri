from btss.tasks import *

class GoNoGratingsOriTask(TaskBase):
    protocol_name = 'GoNoGratingsOri'
    nmax_trials = 3000
    def __init__(self, experiment,
                 rig,
                 windows = None,
                 preference_path = None,
                 reward_volume = 3,     
                 post_reward_duration = 2.5,  # time to collect reward
                 response_period = 3,
                 timeout_duration = 2.5,
                 inter_trial_interval = [1,2],  # seconds (min - max)
                 prob_left = 0.5,
                 audio_volume = 1,
                 visual_par = dict(go_ori = [90],
                                   sf = 0.01,
                                   tf = 0,
                                   nogo_ori = [0],
                                   size = 300,
                                   mask = 'circle',
                                   duration = 2),
                 trial_cue = dict(frequency=2000,
                                  duration=0.25),
                 reward_cue = dict(frequency=9000,
                                   duration=0.25),
                 punishment_cue = dict(duration=1),
                 background = 0,
                 nlicks_to_reward = 2,
                 seed = None,
                 widget = None,
                 **kwargs):
        super(GoNoGratingsOriTask,self).__init__(
            experiment = experiment,
            windows = windows,
            preference_path = preference_path,
            rig = rig,
            **kwargs)

        self.seed = seed
        self.rand = default_rng(self.seed)
        self.background = background
        self.exp.set_background(self.background)
        self.header = ['state',
                       'state_time',
                       'itrial',
                       'iblock',
                       'trial_cue',
                       'reward_cue',
                       'punishment_cue']
        self.trial_frame_cnt = 0
        self.stimframe = -1
        self.audio_volume = audio_volume
        self.block_par = block_par
        self.prob_left = prob_left
        self.reward_volume =  reward_volume
        self.redraw_trials = True
        self.isnewblock = True
        self.block_par = block_par
        self.trial_cue = trial_cue
        self.reward_cue  = reward_cue
        self.punishment_cue = punishment_cue
        self.timeout_duration = timeout_duration
        self.inter_trial_interval = inter_trial_interval
        self.iti_duration = 1
        self.response_period = response_period
        self.post_reward_duration = post_reward_duration
        
        self.last_spout_counts = np.array([0, 0])
        self.trial = None

        self._rewarded_idx = -1
        self._wrong_idx = -1
        
        self.motors_par = motors_par

        self.spout_counts = np.array([0,0])
        self.nlicks_to_reward = nlicks_to_reward

        self.current_block_side = self.rand.choice(['right','left'])
        self.block_count = 0          # count which block we are at
        self.block_ntrials = 0
        self.block_performance = 0

        self.last_trial_side = 0        
        self.task_trial_data = pd.DataFrame([])
        self.task_trial_settings = pd.DataFrame([])
        if not self.exp.gui is None and widget is None:
            from .widget import DynamicForagingWidget,QDockWidget,Qt
            self.widget = DynamicForagingWidget(self)
            w = QDockWidget('DynamicForagingTask',self.exp.gui)
            w.setWidget(self.widget)
            self.exp.gui.addDockWidget(Qt.TopDockWidgetArea,w)
            self.widget.show()
            z = QDockWidget('Task figure',self.exp.gui)
            z.setWidget(self.widget.canvas_widget)
            self.exp.gui.addDockWidget(Qt.BottomDockWidgetArea,z)
            z.show()
        # check if we are using labcams and if so show/take a snapshot to be able to place the subject in the same place in relation to the rig
        self._generate_task_sounds()
        self._post_init_task()

    def _generate_task_sounds(self):
        s = self.rand.uniform(low=-1,
                              high=1,
                              size=int(self.audio_rate*self.punishment_cue['duration']))
        s = np.stack([s,s]).T
        self.punishment_sound = self.exp.sound.Sound(
            s,
            sampleRate = self.audio_rate,
            volume = self.audio_volume)
        t = np.linspace(0,self.reward_cue['duration'],
                        int(self.audio_rate*self.reward_cue['duration']))
        t = np.sin(self.reward_cue['frequency']*np.pi*t)*10
        t = np.stack([t,t]).T
        self.reward_sound = self.exp.sound.Sound(t,
                                                sampleRate = self.audio_rate,
                                                volume = self.audio_volume,
                                                stereo = -1)
        t = np.linspace(0,self.trial_cue['duration'],
                        int(self.audio_rate*self.trial_cue['duration']))
        if not 'frequency' in self.trial_cue:
            self.trial_cue['frequency'] = self.trial_cue['frequency_left']
        t = np.sin(self.trial_cue['frequency']*np.pi*t)
        t = np.stack([t,t]).T
        self.trial_sound = self.exp.sound.Sound(t,
                                                sampleRate = self.audio_rate,
                                                volume = self.audio_volume,
                                                stereo = -1)

    def get_settings(self):
        return dict(reward_volume = self.reward_volume,     
                    post_reward_duration = self.post_reward_duration,
                    response_period = self.response_period,
                    inter_trial_interval = list(self.inter_trial_interval), 
                    motors_par = dict(self.motors_par),
                    trial_cue = dict(self.trial_cue),
                    reward_cue = dict(self.reward_cue),
                    punishment_cue = dict(self.punishment_cue),
                    block_par = dict(self.block_par),
                    audio_volume = self.audio_volume,
                    nlicks_to_reward = self.nlicks_to_reward,
                    background = self.background,
                    seed = self.seed)

    def draw_trials(self):

        if self.trial_list is None:
            self.trial_list = np.zeros(self.nmax_trials,dtype = np.uint8)
        # side of the stim
        self.trial_list[self.itrial:] = np.array(self.rand.random(self.nmax_trials-self.itrial)>self.prob_left)
        self.redraw_trials = False
        
    def evaluate_block_transition(self):
        # check if we are in a new block
        if self.block_ntrials > 4: # try to compute performance
            sel = self.task_trial_data[self.task_trial_data.iblock == self.block_count]
            sel = sel[(sel.rewarded.values == 1) | (sel.punished.values == 1)]
            print(len(sel),flush=True)
            mintrials = np.min(self.block_par['ntrials_exit_criteria'])
            self.block_performance = np.nan
            if len(sel) > mintrials: # only look at 15 trials in the block
                sel = sel.iloc[int(-1*mintrials):]
                self.block_performance = np.sum(sel.rewarded)/len(sel)
            print('Block performance: {0}'.format(self.block_performance), flush = True)
        
        if ((self.block_performance > self.block_par['performance_exit']) and
             (self.block_ntrials > self.min_trials_per_block)):
            self.isnewblock = True
        #end
        if self.isnewblock:
            self.min_trials_per_block =  self.rand.integers(*self.block_par['ntrials_exit_criteria'])
            self.block_performance = 0
            self.current_block_side = 'left' if self.current_block_side == 'right' else 'right' # switch sides
            self.redraw_trials = True
            self.block_count += 1 # count which block we are at
            p = self.rand.choice(self.block_par['probabilities'])
            self.prob_left = 1*p
            if self.current_block_side == 'right':
                self.prob_left = 1-self.prob_left
            if not self.widget is None:
                self.widget.pleft.spin.valueChanged.disconnect()
                self.widget.pleft.spin.setValue(self.prob_left)
                self.widget.pleft.link(self.widget._pleft)

            self.isnewblock = False
        #end
        if self.redraw_trials:
            self.draw_trials()
        #end
        self.block_ntrials += 1

    def trial_init(self):
        self.itrial += 1
        self.trial_frame_cnt = -1
        self.evaluate_block_transition()
        self.lick_counter = None
        self.exp.trial_cnt = self.itrial
        self.exp.stim_cnt = int(self.trial_list[self.itrial]==0)

        trial_side = self.trial_list[self.itrial]==0
        rewarded_side = 'left' if trial_side else 'right'
        if (rewarded_side == 'left'):
            self._rewarded_idx = 0
            self._wrong_idx = 1
            self.trial_cue['frequency'] = self.trial_cue['frequency_left']
        elif (rewarded_side == 'right'):
            self._rewarded_idx = 1
            self._wrong_idx = 0
            self.trial_cue['frequency'] = self.trial_cue['frequency_right']

        try: # in case it changed
            self.response_duration = self.response_period[1]-self.response_period[0]
        except:
            display("Response period needs start and stop times.")
        self._generate_task_sounds()
        self.iti_duration = self.rand.uniform(low = self.inter_trial_interval[0],
                                              high=self.inter_trial_interval[1])

        self.pause = False
        reward_volume = self.reward_volume[self._rewarded_idx]
        self.trial_info = dict(
            itrial = self.itrial,
            rewarded_side = rewarded_side,
            current_block_side = self.current_block_side,
            reward_volume = reward_volume,
            min_trials_per_block = self.min_trials_per_block,
            trial_cue_frequency = self.trial_cue['frequency'],
            reward_cue_frequency = self.reward_cue['frequency'],
            trial_cue_duration = self.trial_cue['duration'],
            reward_cue_duration = self.reward_cue['duration'],
            punishment_cue_duration = self.punishment_cue['duration'],
            response_duration = self.response_duration,
            post_reward_duration = self.post_reward_duration,
            iti_duration = self.iti_duration,
            motors_pos_in = self.motors_par['position_in'],
            motors_pos_out = self.motors_par['position_out'])
        
        self.trial = dict(itrial = self.itrial,
                          iblock = self.block_count,
                          rewarded_side_index = 1 if rewarded_side == 'left' else -1,
                          task_states = [],
                          task_start_time = np.nan,
                          block_performance = self.block_performance,
                          block_side = self.current_block_side,
                          response_time = np.nan,
                          response = 0,
                          rewarded = 0,
                          punished = 0)

        if not self.rig is None:
            self.rig.set_motors(*self.motors_par['position_out'])
            self.rig.set_water_volume(valve0 = self.reward_volume[0],
                                      valve1 = self.reward_volume[1])

        if not self.widget is None:
            self.widget.trial_init_update()
        self.set_state('init')
        self._plot_updated = False
        self._stored = False

    def _handle_response(self, statetime):
        ########################################
        #################RESPONSE###############
        ########################################
        # check if the mouse licks multiple times
        if not self.lick_counter is None: # then there is a rig
            current_licks = self.spout_counts - self.lick_counter
            if current_licks[self._rewarded_idx] >= self.nlicks_to_reward and current_licks[self._wrong_idx] < self.nlicks_to_reward:
                #reward!
                self._give_reward(self._rewarded_idx)
                self._move_wrong_spout()
                self.rewarded_trial = True
                self.trial['response_time'] = self.trial_clock.getTime()
                self.trial['response'] = 1 if self._rewarded_idx == 0 else -1
                self.trial['rewarded'] = 1
                self.play_sound([self.reward_sound])
                self.set_state('post_reward')
            elif current_licks[self._wrong_idx] >= self.nlicks_to_reward: 
                self.trial['response_time'] = self.trial_clock.getTime()
                self.trial['response'] = -1 if self._rewarded_idx == 0 else 1
                self.rig.set_motors(*self.motors_par['position_out'])
                self.play_sound([self.punishment_sound])
                self.set_state('timeout')
        if statetime >= self.response_duration: # no response
            motorpos = [*self.motors_par['position_out']]
            if not self.rig is None:
                self.rig.set_motors(*motorpos)
            self.set_state('iti')

            
    def _evolve_task(self, statetime):
        tolog = [self.state,          # state
                 statetime,           # statetime
                 self.itrial,         # trial number
                 self.block_count,    # iblock
                 None,                # trial_cue
                 None,                # reward_cue
                 None]                # punishment_cue 
        # check for reward if the reward period is ON
        code = 0
        if self.state in ['trial_start']:
            code = 1
            if statetime >= self.trial_cue['duration']:
                tolog[-3] = 1
                self.set_state('response')
                self._start_lick_counter()
        elif self.state in ['response']: 
            self._handle_response(statetime)
        elif self.state in ['post_reward']:
            if statetime <= self.reward_cue['duration']:
                tolog[-2] = 1
            self.trial['rewarded'] = 1
            if statetime >= self.post_reward_duration:
                if not self.rig is None:
                    self.rig.set_motors(*self.motors_par['position_out'])
                self.set_state('iti')
                self.exp.parse_remotes('trial_end')  # send that trial ended
        elif self.state in ['timeout']:
            self.trial['punished'] = 1
            if statetime <= self.punishment_cue['duration']:
                tolog[-1] = 1
            if statetime >= self.timeout_duration:
                self.set_state('iti')
                self.exp.parse_remotes('trial_end')  # send that trial ended
        elif self.state in ['iti']:
            self._handle_iti(statetime)
        return code, tolog

    def _handle_iti(self,statetime):
        if not self._plot_updated:
            if not self.widget is None:
                self.widget.trial_end_update()
                self._plot_updated = True
        if not self._stored:
            self._stored = True
            if self.task_trial_data.empty:
                self.task_trial_data = self.task_trial_data.append([self.trial])
                self.task_trial_data.set_index('itrial')
            else:
                self.task_trial_data = self.task_trial_data.append([self.trial])
            if self.task_trial_settings.empty:
                self.task_trial_settings = self.task_trial_settings.append([self.trial_info])
                self.task_trial_settings.set_index('itrial')
            else:
                self.task_trial_settings = self.task_trial_settings.append([self.trial_info])
        if statetime >= self.iti_duration:
            self.state = None

    def evolve(self):
        code = 0
        self.trial_frame_cnt += 1
        if not self.rig is None:
            self.spout_counts = np.array([self.rig.lick0['counter'].value,
                                          self.rig.lick1['counter'].value])
        
        statetime = self.state_clock.getTime()
        if self.state is None and not self.pause:
            self.trial_init()          # increment trial count, generate stimuli don't draw anything
            return 0, None
        elif self.pause:
            return 0, None              # when it is paused do nothing
        if self.state in ['init']:
            self.stim_order_cnt += 1
            # start the clock
            self.trial_clock.reset()
            if not self.rig is None:
                self.rig.send_trial_pulse()
            self.trial['task_start_time'] = self.exp.clock.getTime()
            self.exp.parse_remotes('trial_start')
            self.set_state('trial_start')
            # play trial cue?
            self.play_sound([self.trial_sound])
            return 0, [self.state,     # state
                       statetime,      # statetime
                       self.itrial,    # trial number
                       0,              # visual punishment frame
                       0,              # audio punishment frame
                       None,None,      # visual pos left x,y
                       None,None,      # visual pos right x,y
                       None,None]      # has audio event left,right 
        else:
            c,log =  self._evolve_task(statetime)    
        return c, log               


    def _start_lick_counter(self, no_motor_motion=False):
        self.lick_counter = None
        self.rewarded_trial = False
        if not self.rig is None:
            if not no_motor_motion:
                motorpos = [*self.motors_par['position_in']]
                self.rig.set_motors(*motorpos)                
            self.lick_counter = np.array([self.rig.lick0['counter'].value,
                                          self.rig.lick1['counter'].value])

    def stop(self):
        self.stop_sound()
        duration = self.exp.clock.getTime()
        # get the subject weight
        subject_weight = None  
        if not self.exp.gui is None:
            if hasattr(self.exp.gui,'subject_weight'):
                if not self.exp.gui.subject_weight is None:
                    subject_weight = self.exp.gui.subject_weight
        # get the water volume
        watervolume = np.sum(self.task_trial_data.rewarded*self.task_trial_settings.reward_volume)/1000.
                    
        print('''
        Subject: {0}
        Session: {1}
           weight: {2} g
           water: {3} mL
           ntrials: {4} 
           duration: {5} min

'''.format(self.exp.subject_name,
           self.exp.start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
           subject_weight,
           watervolume,
           len(self.task_trial_data),
           duration/60.), flush=True)
        prefs = get_preferences(self.exp.user)
        path = prefs['log_path']
        
        self.save_settings_to_file()

        filename = pjoin(path, self.exp.experiment_folder(),
                         '{0}_{1}_{2}.triallog.h5'.format(
                             self.exp.subject_name,
                             self.exp.start_datetime.strftime('%Y%m%d_%H%M%S'),
                             self.protocol_name))
        if self.itrial < 5: # there are too little trials, not saving
            print('Not saving because there are too few trials.',flush=True)
            return
        if self._saved_data:
            print('Data were already saved',flush=True)
        data = self.task_trial_settings.merge(self.task_trial_data)
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        data.to_hdf(filename,'task')
        self.save_settings(fname = pjoin(path, self.exp.experiment_folder(),'{0}.yaml'.format(self.protocol_name)))
        print('Saved {0}'.format(filename))
        import h5py as h5
        with h5.File(filename,'a') as f:
            if not 'subject_name' in f.keys():
                f.create_dataset('subject_name', data = self.exp.subject_name)
            else:
                f['subject_name'] = self.exp.subject_name
            if not 'date' in f.keys():
                f.create_dataset('date',data=self.exp.start_datetime.strftime('%Y-%m-%d %H:%M:%S'))
            else:
                f['date'] = self.exp.start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            if not subject_weight is None:
                if 'subject_weight' in f.keys():
                    f['subject_weight'] = subject_weight
                else:
                    f.create_dataset('subject_weight',
                                     data = subject_weight)
        
        self._saved_data=True
        
    def _move_wrong_spout(self):
        if not self.rig is None:
            M1,M2 = self.motors_par['position_in']
            M1o,M2o = self.motors_par['position_out']
            if self._wrong_idx == 1:#(self.trial_info['rewarded_side'] == 'left'):
                M2 = M2o
            else:
                M1 = M1o
            self.rig.set_motors(M1,M2)

    def _give_reward(self,rewarded_idx, flipandwait=False):
        if not self.rig is None:
            self.rig.give_water(rewarded_idx)

        
