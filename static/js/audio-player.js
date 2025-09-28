/**
 * Harmony Audio Player - Intelligent Redesign
 * A robust, state-driven audio player with advanced error handling and user experience
 */

class HarmonyAudioPlayer {
    constructor() {
        // Core audio state
        this.audio = null;
        this.currentTrack = null;
        this.isPlaying = false;
        this.isLoading = false;
        this.currentTime = 0;
        this.duration = 0;
        this.buffered = 0;
        
        // Player settings
        this.volume = 1.0;
        this.isMuted = false;
        this.isShuffled = false;
        this.repeatMode = 'none'; // 'none', 'one', 'all'
        
        // Playlist management
        this.playlist = [];
        this.currentIndex = -1;
        this.history = [];
        this.queue = [];
        
        // Error handling and retry logic
        this.retryCount = 0;
        this.maxRetries = 3;
        this.retryDelay = 1000;
        
        // Performance optimization
        this.preloadedTracks = new Map();
        this.maxPreloadedTracks = 3;
        
        // UI state
        this.isVisible = false;
        this.isMinimized = false;
        
        // Event listeners storage for cleanup
        this.eventListeners = new Map();
        
        // Initialize player
        this.init();
    }
    
    /**
     * Initialize the audio player
     */
    async init() {
        try {
            await this.createPlayerHTML();
            this.bindEvents();
            this.loadSettings();
            this.setupGlobalPlayButtons();
            this.startPerformanceMonitoring();
            
            console.log('Harmony Audio Player initialized successfully');
        } catch (error) {
            console.error('Failed to initialize audio player:', error);
            this.showError('Failed to initialize audio player');
        }
    }
    
    /**
     * Create the player HTML structure
     */
    async createPlayerHTML() {
        const playerHTML = `
            <div id="harmony-player" class="harmony-player" role="region" aria-label="Audio Player">
                <div class="player-container">
                    <!-- Track Info Section -->
                    <div class="track-info">
                        <div class="track-artwork" id="track-artwork">
                            <i class="fas fa-music" aria-hidden="true"></i>
                            <div class="artwork-overlay">
                                <div class="loading-spinner" id="artwork-spinner"></div>
                            </div>
                        </div>
                        <div class="track-details">
                            <div class="track-title" id="track-title">Select a track to play</div>
                            <div class="track-artist" id="track-artist">Harmony Music</div>
                            <div class="track-album" id="track-album"></div>
                        </div>
                    </div>
                    
                    <!-- Player Controls Section -->
                    <div class="player-controls">
                        <div class="control-buttons">
                            <button class="control-btn shuffle-btn" id="shuffle-btn" title="Toggle Shuffle" aria-label="Toggle Shuffle">
                                <i class="fas fa-random" aria-hidden="true"></i>
                            </button>
                            <button class="control-btn prev-btn" id="prev-btn" title="Previous Track" aria-label="Previous Track">
                                <i class="fas fa-step-backward" aria-hidden="true"></i>
                            </button>
                            <button class="control-btn play-pause-btn" id="play-pause-btn" title="Play" aria-label="Play">
                                <i class="fas fa-play" aria-hidden="true"></i>
                            </button>
                            <button class="control-btn next-btn" id="next-btn" title="Next Track" aria-label="Next Track">
                                <i class="fas fa-step-forward" aria-hidden="true"></i>
                            </button>
                            <button class="control-btn repeat-btn" id="repeat-btn" title="Toggle Repeat" aria-label="Toggle Repeat">
                                <i class="fas fa-redo" aria-hidden="true"></i>
                            </button>
                        </div>
                        
                        <div class="progress-container">
                            <span class="time-current" id="time-current">0:00</span>
                            <div class="progress-bar" id="progress-bar" role="slider" aria-label="Seek" tabindex="0">
                                <div class="progress-track">
                                    <div class="progress-buffered" id="progress-buffered"></div>
                                    <div class="progress-fill" id="progress-fill"></div>
                                    <div class="progress-handle" id="progress-handle"></div>
                                </div>
                            </div>
                            <span class="time-duration" id="time-duration">0:00</span>
                        </div>
                    </div>
                    
                    <!-- Player Extras Section -->
                    <div class="player-extras">
                        <button class="control-btn like-btn" id="like-btn" title="Like Track" aria-label="Like Track">
                            <i class="far fa-heart" aria-hidden="true"></i>
                        </button>
                        <button class="control-btn playlist-btn" id="playlist-btn" title="Add to Playlist" aria-label="Add to Playlist">
                            <i class="fas fa-plus" aria-hidden="true"></i>
                        </button>
                        <div class="volume-container">
                            <button class="control-btn volume-btn" id="volume-btn" title="Toggle Mute" aria-label="Toggle Mute">
                                <i class="fas fa-volume-up" aria-hidden="true"></i>
                            </button>
                            <div class="volume-slider" id="volume-slider" role="slider" aria-label="Volume" tabindex="0">
                                <div class="volume-track">
                                    <div class="volume-fill" id="volume-fill"></div>
                                    <div class="volume-handle" id="volume-handle"></div>
                                </div>
                            </div>
                        </div>
                        <button class="control-btn queue-btn" id="queue-btn" title="Show Queue" aria-label="Show Queue">
                            <i class="fas fa-list" aria-hidden="true"></i>
                        </button>
                        <button class="control-btn minimize-btn" id="minimize-btn" title="Minimize Player" aria-label="Minimize Player">
                            <i class="fas fa-chevron-down" aria-hidden="true"></i>
                        </button>
                    </div>
                </div>
                
                <!-- Status Indicators -->
                <div class="player-status">
                    <div class="status-indicator loading" id="loading-indicator">
                        <div class="loading-spinner"></div>
                        <span>Loading...</span>
                    </div>
                    <div class="status-indicator error" id="error-indicator">
                        <i class="fas fa-exclamation-triangle" aria-hidden="true"></i>
                        <span id="error-message">An error occurred</span>
                        <div class="error-actions">
                            <button class="retry-btn" id="retry-btn">Retry</button>
                            <button class="cancel-btn" id="cancel-btn">Cancel</button>
                        </div>
                    </div>
                    <div class="status-indicator buffering" id="buffering-indicator">
                        <div class="buffering-spinner"></div>
                        <span>Buffering...</span>
                    </div>
                </div>
                
                <!-- Queue Panel -->
                <div class="queue-panel" id="queue-panel">
                    <div class="queue-header">
                        <h3>Up Next</h3>
                        <button class="close-queue" id="close-queue" aria-label="Close Queue">
                            <i class="fas fa-times" aria-hidden="true"></i>
                        </button>
                    </div>
                    <div class="queue-list" id="queue-list">
                        <div class="queue-empty">
                            <i class="fas fa-music" aria-hidden="true"></i>
                            <p>No tracks in queue</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add player to body
        document.body.insertAdjacentHTML('beforeend', playerHTML);
        this.playerElement = document.getElementById('harmony-player');
        
        // Cache frequently used elements
        this.cacheElements();
    }
    
    /**
     * Cache frequently used DOM elements for performance
     */
    cacheElements() {
        this.elements = {
            // Track info
            trackArtwork: document.getElementById('track-artwork'),
            trackTitle: document.getElementById('track-title'),
            trackArtist: document.getElementById('track-artist'),
            trackAlbum: document.getElementById('track-album'),
            
            // Controls
            playPauseBtn: document.getElementById('play-pause-btn'),
            prevBtn: document.getElementById('prev-btn'),
            nextBtn: document.getElementById('next-btn'),
            shuffleBtn: document.getElementById('shuffle-btn'),
            repeatBtn: document.getElementById('repeat-btn'),
            likeBtn: document.getElementById('like-btn'),
            playlistBtn: document.getElementById('playlist-btn'),
            volumeBtn: document.getElementById('volume-btn'),
            queueBtn: document.getElementById('queue-btn'),
            minimizeBtn: document.getElementById('minimize-btn'),
            
            // Progress
            progressBar: document.getElementById('progress-bar'),
            progressFill: document.getElementById('progress-fill'),
            progressBuffered: document.getElementById('progress-buffered'),
            progressHandle: document.getElementById('progress-handle'),
            timeCurrent: document.getElementById('time-current'),
            timeDuration: document.getElementById('time-duration'),
            
            // Volume
            volumeSlider: document.getElementById('volume-slider'),
            volumeFill: document.getElementById('volume-fill'),
            volumeHandle: document.getElementById('volume-handle'),
            
            // Status
            loadingIndicator: document.getElementById('loading-indicator'),
            errorIndicator: document.getElementById('error-indicator'),
            bufferingIndicator: document.getElementById('buffering-indicator'),
            errorMessage: document.getElementById('error-message'),
            retryBtn: document.getElementById('retry-btn'),
            cancelBtn: document.getElementById('cancel-btn'),
            
            // Queue
            queuePanel: document.getElementById('queue-panel'),
            queueList: document.getElementById('queue-list'),
            closeQueue: document.getElementById('close-queue')
        };
    }
    
    /**
     * Bind all event listeners
     */
    bindEvents() {
        // Control button events
        this.addEventListener(this.elements.playPauseBtn, 'click', () => this.togglePlayPause());
        this.addEventListener(this.elements.prevBtn, 'click', () => this.previousTrack());
        this.addEventListener(this.elements.nextBtn, 'click', () => this.nextTrack());
        this.addEventListener(this.elements.shuffleBtn, 'click', () => this.toggleShuffle());
        this.addEventListener(this.elements.repeatBtn, 'click', () => this.toggleRepeat());
        this.addEventListener(this.elements.likeBtn, 'click', () => this.toggleLike());
        this.addEventListener(this.elements.playlistBtn, 'click', () => this.showPlaylistMenu());
        this.addEventListener(this.elements.volumeBtn, 'click', () => this.toggleMute());
        this.addEventListener(this.elements.queueBtn, 'click', () => this.toggleQueue());
        this.addEventListener(this.elements.minimizeBtn, 'click', () => this.toggleMinimize());
        
        // Progress bar events
        this.addEventListener(this.elements.progressBar, 'click', (e) => this.seekTo(e));
        this.addEventListener(this.elements.progressBar, 'keydown', (e) => this.handleProgressKeydown(e));
        
        // Volume slider events
        this.addEventListener(this.elements.volumeSlider, 'click', (e) => this.setVolume(e));
        this.addEventListener(this.elements.volumeSlider, 'keydown', (e) => this.handleVolumeKeydown(e));
        
        // Status events
        this.addEventListener(this.elements.retryBtn, 'click', () => this.retryCurrentTrack());
        this.addEventListener(this.elements.cancelBtn, 'click', () => this.cancelError());
        this.addEventListener(this.elements.closeQueue, 'click', () => this.hideQueue());
        
        // Global keyboard shortcuts\n        this.addEventListener(document, 'keydown', (e) => this.handleKeyboard(e));
        
        // Window events for cleanup\n        this.addEventListener(window, 'beforeunload', () => this.cleanup());
        
        // Media session API for system integration\n        this.setupMediaSession();
    }
    
    /**
     * Add event listener with cleanup tracking
     */
    addEventListener(element, event, handler) {
        element.addEventListener(event, handler);
        
        if (!this.eventListeners.has(element)) {
            this.eventListeners.set(element, []);
        }
        this.eventListeners.get(element).push({ event, handler });
    }
    
    /**
     * Setup global play buttons throughout the application
     */
    setupGlobalPlayButtons() {
        // Use event delegation for better performance
        this.addEventListener(document, 'click', (e) => {
            const playBtn = e.target.closest('.play-track-btn, [data-track-id]');
            if (playBtn) {
                e.preventDefault();
                const trackId = playBtn.dataset.trackId || playBtn.getAttribute('data-track-id');
                if (trackId) {
                    this.loadTrack(parseInt(trackId), true);
                }
            }
        });
    }
    
    /**
     * Load and play a track with intelligent error handling and preloading
     */
    async loadTrack(trackId, autoPlay = true) {
        try {
            console.log(`Loading track ${trackId}...`);
            
            // Prevent multiple simultaneous loads
            if (this.isLoading) {
                console.log('Already loading a track, ignoring request');
                return;
            }
            
            this.isLoading = true;
            this.showStatus('loading');
            this.retryCount = 0;
            
            // Check if track is already preloaded
            if (this.preloadedTracks.has(trackId)) {
                console.log('Using preloaded track data');
                const preloadedData = this.preloadedTracks.get(trackId);
                await this.setupAudioWithTrack(preloadedData, autoPlay);
                return;
            }
            
            // Fetch track info
            const trackInfo = await this.fetchTrackInfo(trackId);
            await this.setupAudioWithTrack(trackInfo, autoPlay);
            
            // Preload next tracks in queue/playlist
            this.preloadNextTracks();
            
        } catch (error) {
            console.error('Error loading track:', error);
            await this.handleLoadError(error, trackId, autoPlay);
        } finally {
            this.isLoading = false;
        }
    }
    
    /**
     * Fetch track information with retry logic
     */
    async fetchTrackInfo(trackId) {
        const maxRetries = 3;
        let lastError;
        
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                console.log(`Fetching track info (attempt ${attempt}/${maxRetries})...`);
                
                const response = await fetch(`/api/track/${trackId}/info`, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Cache-Control': 'no-cache'
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const trackInfo = await response.json();
                console.log('Track info loaded:', trackInfo);
                return trackInfo;
                
            } catch (error) {
                lastError = error;
                console.warn(`Attempt ${attempt} failed:`, error.message);
                
                if (attempt < maxRetries) {
                    await this.delay(1000 * attempt); // Exponential backoff
                }
            }
        }
        
        throw lastError;
    }
    
    /**
     * Setup audio element with track data
     */
    async setupAudioWithTrack(trackInfo, autoPlay) {
        // Clean up previous audio
        this.cleanupAudio();
        
        // Update current track info
        this.currentTrack = trackInfo;
        this.updateTrackInfo(trackInfo);
        
        // Create new audio element
        const audioUrl = `/audio/${trackInfo.id}`;
        console.log('Creating audio element with URL:', audioUrl);
        
        this.audio = new Audio();
        this.audio.preload = 'auto';
        this.audio.volume = this.isMuted ? 0 : this.volume;
        this.audio.crossOrigin = 'anonymous'; // For CORS if needed
        
        // Setup audio event listeners
        this.setupAudioEvents();
        
        // Set source and load
        this.audio.src = audioUrl;
        this.audio.load();
        
        // Show player and update UI
        this.show();
        this.updatePlayButton(false);
        this.hideStatus();
        
        // Auto play if requested
        if (autoPlay) {
            // Wait for enough data to play
            await this.waitForCanPlay();
            await this.play();
        }
    }
    
    /**
     * Setup audio element event listeners
     */
    setupAudioEvents() {
        if (!this.audio) return;
        
        // Playback events
        this.audio.addEventListener('loadstart', () => this.onLoadStart());
        this.audio.addEventListener('loadedmetadata', () => this.onLoadedMetadata());
        this.audio.addEventListener('loadeddata', () => this.onLoadedData());
        this.audio.addEventListener('canplay', () => this.onCanPlay());
        this.audio.addEventListener('canplaythrough', () => this.onCanPlayThrough());
        this.audio.addEventListener('play', () => this.onPlay());
        this.audio.addEventListener('pause', () => this.onPause());
        this.audio.addEventListener('ended', () => this.onEnded());
        this.audio.addEventListener('timeupdate', () => this.onTimeUpdate());
        this.audio.addEventListener('progress', () => this.onProgress());
        this.audio.addEventListener('waiting', () => this.onWaiting());
        this.audio.addEventListener('playing', () => this.onPlaying());
        this.audio.addEventListener('seeked', () => this.onSeeked());
        
        // Error events
        this.audio.addEventListener('error', (e) => this.onAudioError(e));
        this.audio.addEventListener('stalled', () => this.onStalled());
        this.audio.addEventListener('suspend', () => this.onSuspend());
        this.audio.addEventListener('abort', () => this.onAbort());
    }
    
    /**
     * Wait for audio to be ready to play with better error handling
     */
    waitForCanPlay() {
        return new Promise((resolve, reject) => {
            if (!this.audio) {
                reject(new Error('No audio element'));
                return;
            }
            
            // Check if already ready
            if (this.audio.readyState >= 2) { // HAVE_CURRENT_DATA or better
                console.log('Audio already ready, readyState:', this.audio.readyState);
                resolve();
                return;
            }
            
            console.log('Waiting for audio to be ready, current readyState:', this.audio.readyState);
            
            const timeout = setTimeout(() => {
                this.audio.removeEventListener('canplay', onCanPlay);
                this.audio.removeEventListener('canplaythrough', onCanPlayThrough);
                this.audio.removeEventListener('loadeddata', onLoadedData);
                this.audio.removeEventListener('error', onError);
                console.warn('Audio timeout - attempting to play anyway');
                resolve(); // Don't reject, try to play anyway
            }, 5000); // Reduced timeout to 5 seconds
            
            const onCanPlay = () => {
                console.log('Audio can play');
                clearTimeout(timeout);
                this.audio.removeEventListener('canplay', onCanPlay);
                this.audio.removeEventListener('canplaythrough', onCanPlayThrough);
                this.audio.removeEventListener('loadeddata', onLoadedData);
                this.audio.removeEventListener('error', onError);
                resolve();
            };
            
            const onCanPlayThrough = () => {
                console.log('Audio can play through');
                clearTimeout(timeout);
                this.audio.removeEventListener('canplay', onCanPlay);
                this.audio.removeEventListener('canplaythrough', onCanPlayThrough);
                this.audio.removeEventListener('loadeddata', onLoadedData);
                this.audio.removeEventListener('error', onError);
                resolve();
            };
            
            const onLoadedData = () => {
                console.log('Audio data loaded');
                clearTimeout(timeout);
                this.audio.removeEventListener('canplay', onCanPlay);
                this.audio.removeEventListener('canplaythrough', onCanPlayThrough);
                this.audio.removeEventListener('loadeddata', onLoadedData);
                this.audio.removeEventListener('error', onError);
                resolve();
            };
            
            const onError = (e) => {
                console.error('Audio error while waiting:', e);
                clearTimeout(timeout);
                this.audio.removeEventListener('canplay', onCanPlay);
                this.audio.removeEventListener('canplaythrough', onCanPlayThrough);
                this.audio.removeEventListener('loadeddata', onLoadedData);
                this.audio.removeEventListener('error', onError);
                reject(new Error('Audio error: ' + (e.message || 'Unknown error')));
            };
            
            // Listen for multiple events that indicate readiness
            this.audio.addEventListener('canplay', onCanPlay);
            this.audio.addEventListener('canplaythrough', onCanPlayThrough);
            this.audio.addEventListener('loadeddata', onLoadedData);
            this.audio.addEventListener('error', onError);
        });
    }
    
    /**
     * Play audio with error handling
     */
    async play() {
        if (!this.audio) {
            throw new Error('No audio element available');
        }
        
        try {
            console.log('Attempting to play audio...');
            
            // Check if we can play
            if (this.audio.readyState < 3) {
                console.log('Audio not ready, waiting...');
                await this.waitForCanPlay();
            }
            
            const playPromise = this.audio.play();
            
            if (playPromise !== undefined) {
                await playPromise;
                console.log('Audio playback started successfully');
                this.isPlaying = true;
                this.updatePlayButton(true);
                await this.trackPlayActivity();
            }
            
        } catch (error) {
            console.error('Error playing audio:', error);
            this.isPlaying = false;
            this.updatePlayButton(false);
            
            // Handle specific error types
            if (error.name === 'NotAllowedError') {
                this.showError('Click to play - browser requires user interaction', false);
            } else if (error.name === 'NotSupportedError') {
                this.showError('Audio format not supported', true);
            } else if (error.name === 'AbortError') {
                this.showError('Playback was aborted', true);
            } else {
                this.showError(`Failed to play: ${error.message}`, true);
            }
            
            throw error;
        }
    }
    
    /**
     * Pause audio
     */
    pause() {
        if (!this.audio) return;
        
        try {
            this.audio.pause();
            this.isPlaying = false;
            this.updatePlayButton(false);
            console.log('Audio paused');
        } catch (error) {
            console.error('Error pausing audio:', error);
        }
    }
    
    /**
     * Toggle play/pause
     */
    async togglePlayPause() {
        if (!this.audio) {
            console.log('No audio loaded');
            return;
        }
        
        try {
            if (this.isPlaying) {
                this.pause();
            } else {
                await this.play();
            }
        } catch (error) {
            console.error('Error toggling playback:', error);
        }
    }
    
    /**
     * Play previous track
     */
    async previousTrack() {
        if (this.history.length > 0) {
            const previousTrack = this.history.pop();
            await this.loadTrack(previousTrack.id);
        } else if (this.playlist.length > 0) {
            this.currentIndex = this.currentIndex > 0 ? this.currentIndex - 1 : this.playlist.length - 1;
            await this.loadTrack(this.playlist[this.currentIndex].id);
        }
    }
    
    /**
     * Play next track
     */
    async nextTrack() {
        // Add current track to history
        if (this.currentTrack) {
            this.history.push(this.currentTrack);
            if (this.history.length > 50) { // Limit history size
                this.history.shift();
            }
        }
        
        // Check queue first
        if (this.queue.length > 0) {
            const nextTrack = this.queue.shift();
            await this.loadTrack(nextTrack.id);
            this.updateQueueDisplay();
            return;
        }
        
        // Then check playlist
        if (this.playlist.length > 0) {
            if (this.isShuffled) {
                this.currentIndex = Math.floor(Math.random() * this.playlist.length);
            } else {
                this.currentIndex = this.currentIndex < this.playlist.length - 1 ? this.currentIndex + 1 : 0;
            }
            await this.loadTrack(this.playlist[this.currentIndex].id);
        }
    }
    
    /**
     * Seek to specific time
     */
    seekTo(event) {
        if (!this.audio || !this.duration) return;
        
        const progressBar = event.currentTarget;
        const rect = progressBar.getBoundingClientRect();
        const percent = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
        const seekTime = percent * this.duration;
        
        console.log(`Seeking to ${seekTime}s (${Math.round(percent * 100)}%)`);
        
        try {
            this.audio.currentTime = seekTime;
            this.updateProgress();
        } catch (error) {
            console.error('Error seeking:', error);
        }
    }
    
    /**
     * Set volume
     */
    setVolume(event) {
        const volumeSlider = event.currentTarget;
        const rect = volumeSlider.getBoundingClientRect();
        const percent = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
        
        this.volume = percent;
        
        if (this.audio && !this.isMuted) {
            this.audio.volume = this.volume;
        }
        
        this.updateVolumeDisplay();
        this.saveSettings();
        
        console.log(`Volume set to ${Math.round(percent * 100)}%`);
    }
    
    /**
     * Toggle mute
     */
    toggleMute() {
        if (!this.audio) return;
        
        this.isMuted = !this.isMuted;
        this.audio.volume = this.isMuted ? 0 : this.volume;
        this.updateVolumeDisplay();
        this.saveSettings();
        
        console.log(`Audio ${this.isMuted ? 'muted' : 'unmuted'}`);
    }
    
    /**
     * Toggle shuffle
     */
    toggleShuffle() {
        this.isShuffled = !this.isShuffled;
        this.updateShuffleButton();
        this.saveSettings();
        
        console.log(`Shuffle ${this.isShuffled ? 'enabled' : 'disabled'}`);
    }
    
    /**
     * Toggle repeat mode
     */
    toggleRepeat() {
        const modes = ['none', 'one', 'all'];
        const currentIndex = modes.indexOf(this.repeatMode);
        this.repeatMode = modes[(currentIndex + 1) % modes.length];
        this.updateRepeatButton();
        this.saveSettings();
        
        console.log(`Repeat mode: ${this.repeatMode}`);
    }
    
    /**
     * Toggle like for current track
     */
    async toggleLike() {
        if (!this.currentTrack) return;
        
        try {
            const response = await fetch(`/client/track/${this.currentTrack.id}/like`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            if (result.status === 'success') {
                this.updateLikeButton(true);
                this.showNotification('Track liked!');
            } else {
                this.showNotification('Failed to like track', 'error');
            }
        } catch (error) {
            console.error('Error liking track:', error);
            this.showNotification('Error liking track', 'error');
        }
    }
    
    /**
     * Show playlist menu
     */
    showPlaylistMenu() {
        if (!this.currentTrack) return;
        
        // This would show a modal or dropdown with playlist options
        // For now, we'll use a simple prompt
        const playlistName = prompt('Enter playlist name to add this track:');
        if (playlistName) {
            this.addToPlaylist(playlistName);
        }
    }
    
    /**
     * Add current track to playlist
     */
    async addToPlaylist(playlistName) {
        // Implementation would depend on your playlist API
        console.log(`Adding track to playlist: ${playlistName}`);
        this.showNotification(`Added to playlist: ${playlistName}`);
    }
    
    /**
     * Toggle queue panel
     */
    toggleQueue() {
        const isVisible = this.elements.queuePanel.classList.contains('visible');
        if (isVisible) {
            this.hideQueue();
        } else {
            this.showQueue();
        }
    }
    
    /**
     * Show queue panel
     */
    showQueue() {
        this.elements.queuePanel.classList.add('visible');
        this.updateQueueDisplay();
    }
    
    /**
     * Hide queue panel
     */
    hideQueue() {
        this.elements.queuePanel.classList.remove('visible');
    }
    
    /**
     * Update queue display
     */
    updateQueueDisplay() {
        const queueList = this.elements.queueList;
        
        if (this.queue.length === 0) {
            queueList.innerHTML = `
                <div class="queue-empty">
                    <i class="fas fa-music" aria-hidden="true"></i>
                    <p>No tracks in queue</p>
                </div>
            `;
            return;
        }
        
        const queueHTML = this.queue.map((track, index) => `
            <div class="queue-item" data-index="${index}">
                <div class="queue-track-info">
                    <div class="queue-track-title">${track.title}</div>
                    <div class="queue-track-artist">${track.artist}</div>
                </div>
                <button class="queue-remove" onclick="harmonyPlayer.removeFromQueue(${index})" aria-label="Remove from queue">
                    <i class="fas fa-times" aria-hidden="true"></i>
                </button>
            </div>
        `).join('');
        
        queueList.innerHTML = queueHTML;
    }
    
    /**
     * Add track to queue
     */
    addToQueue(track) {
        this.queue.push(track);
        this.updateQueueDisplay();
        this.showNotification(`Added "${track.title}" to queue`);
    }
    
    /**
     * Remove track from queue
     */
    removeFromQueue(index) {
        if (index >= 0 && index < this.queue.length) {
            const removedTrack = this.queue.splice(index, 1)[0];
            this.updateQueueDisplay();
            this.showNotification(`Removed "${removedTrack.title}" from queue`);
        }
    }
    
    /**
     * Toggle minimize player
     */
    toggleMinimize() {
        this.isMinimized = !this.isMinimized;
        this.playerElement.classList.toggle('minimized', this.isMinimized);
        
        const icon = this.elements.minimizeBtn.querySelector('i');
        icon.className = this.isMinimized ? 'fas fa-chevron-up' : 'fas fa-chevron-down';
        
        // Update button title
        this.elements.minimizeBtn.title = this.isMinimized ? 'Expand Player' : 'Minimize Player';
        this.elements.minimizeBtn.setAttribute('aria-label', this.isMinimized ? 'Expand Player' : 'Minimize Player');
    }
    
    /**
     * Show player
     */
    show() {
        if (!this.isVisible) {
            this.isVisible = true;
            this.playerElement.classList.add('visible');
            console.log('Player shown');
        }
    }
    
    /**
     * Hide player
     */
    hide() {
        if (this.isVisible) {
            this.isVisible = false;
            this.playerElement.classList.remove('visible');
            console.log('Player hidden');
        }
    }
    
    /**
     * Show status indicator
     */
    showStatus(type) {
        // Hide all status indicators first
        this.elements.loadingIndicator.style.display = 'none';
        this.elements.errorIndicator.style.display = 'none';
        this.elements.bufferingIndicator.style.display = 'none';
        
        // Show requested status
        switch (type) {
            case 'loading':
                this.elements.loadingIndicator.style.display = 'flex';
                break;
            case 'error':
                this.elements.errorIndicator.style.display = 'flex';
                break;
            case 'buffering':
                this.elements.bufferingIndicator.style.display = 'flex';
                break;
        }
    }
    
    /**
     * Hide all status indicators
     */
    hideStatus() {
        this.elements.loadingIndicator.style.display = 'none';
        this.elements.errorIndicator.style.display = 'none';
        this.elements.bufferingIndicator.style.display = 'none';
    }
    
    /**
     * Show error with retry option
     */
    showError(message, canRetry = true) {
        console.error('Player error:', message);
        this.elements.errorMessage.textContent = message;
        this.elements.retryBtn.style.display = canRetry ? 'block' : 'none';
        this.showStatus('error');
        this.showNotification(message, 'error');
    }
    
    /**
     * Retry current track
     */
    async retryCurrentTrack() {
        if (this.currentTrack) {
            console.log('Retrying current track...');
            await this.loadTrack(this.currentTrack.id, this.isPlaying);
        }
    }
    
    /**
     * Cancel error and hide error indicator
     */
    cancelError() {
        console.log('Canceling error...');
        this.hideStatus();
        this.retryCount = 0; // Reset retry count
        
        // Clean up any problematic audio
        this.cleanupAudio();
        
        // Reset player state
        this.isPlaying = false;
        this.updatePlayButton(false);
        
        console.log('Error canceled');
    }
    
    /**
     * Handle load error with intelligent retry
     */
    async handleLoadError(error, trackId, autoPlay) {
        this.retryCount++;
        
        if (this.retryCount <= this.maxRetries) {
            console.log(`Retrying track load (${this.retryCount}/${this.maxRetries})...`);
            await this.delay(this.retryDelay * this.retryCount);
            
            try {
                await this.loadTrack(trackId, autoPlay);
                return;
            } catch (retryError) {
                console.error('Retry failed:', retryError);
            }
        }
        
        // All retries failed
        this.showError(`Failed to load track: ${error.message}`, true);
    }
    
    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `player-notification ${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : 'info-circle'}" aria-hidden="true"></i>
            <span>${message}</span>
        `;
        
        this.playerElement.appendChild(notification);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    }
    
    // Audio Event Handlers
    onLoadStart() {
        console.log('Audio load started');
        this.showStatus('loading');
    }
    
    onLoadedMetadata() {
        this.duration = this.audio.duration;
        this.updateDuration();
        this.updateProgress();
        console.log('Audio metadata loaded, duration:', this.duration);
    }
    
    onLoadedData() {
        console.log('Audio data loaded');
    }
    
    onCanPlay() {
        this.hideStatus();
        console.log('Audio can play');
    }
    
    onCanPlayThrough() {
        console.log('Audio can play through');
    }
    
    onPlay() {
        this.isPlaying = true;
        this.updatePlayButton(true);
        console.log('Audio started playing');
    }
    
    onPause() {
        this.isPlaying = false;
        this.updatePlayButton(false);
        console.log('Audio paused');
    }
    
    async onEnded() {
        this.isPlaying = false;
        this.updatePlayButton(false);
        console.log('Audio ended');
        
        // Handle repeat modes
        if (this.repeatMode === 'one') {
            try {
                console.log('Repeating current track...');
                this.audio.currentTime = 0;
                await this.play();
            } catch (error) {
                console.error('Error repeating track:', error);
                // If repeat fails, show error but don't freeze
                this.showError(`Failed to repeat track: ${error.message}`, true);
            }
        } else if (this.repeatMode === 'all' || this.queue.length > 0 || this.currentIndex < this.playlist.length - 1) {
            try {
                await this.nextTrack();
            } catch (error) {
                console.error('Error playing next track:', error);
                this.showError(`Failed to play next track: ${error.message}`, true);
            }
        }
    }
    
    onTimeUpdate() {
        this.currentTime = this.audio.currentTime;
        this.updateProgress();
    }
    
    onProgress() {
        this.updateBuffered();
    }
    
    onWaiting() {
        console.log('Audio waiting for data');
        this.showStatus('buffering');
    }
    
    onPlaying() {
        console.log('Audio playing');
        this.hideStatus();
    }
    
    onSeeked() {
        console.log('Audio seeked to:', this.audio.currentTime);
    }
    
    onAudioError(event) {
        const error = this.audio.error;
        let message = 'Unknown audio error';
        
        if (error) {
            switch (error.code) {
                case error.MEDIA_ERR_ABORTED:
                    message = 'Audio playback was aborted';
                    break;
                case error.MEDIA_ERR_NETWORK:
                    message = 'Network error occurred';
                    break;
                case error.MEDIA_ERR_DECODE:
                    message = 'Audio decoding error';
                    break;
                case error.MEDIA_ERR_SRC_NOT_SUPPORTED:
                    message = 'Audio format not supported';
                    break;
            }
        }
        
        console.error('Audio error:', error, message);
        this.showError(message, true);
    }
    
    onStalled() {
        console.warn('Audio stalled');
        this.showStatus('buffering');
    }
    
    onSuspend() {
        console.log('Audio suspended');
    }
    
    onAbort() {
        console.log('Audio aborted');
    }
    
    // UI Update Methods
    updateTrackInfo(trackInfo) {
        this.elements.trackTitle.textContent = trackInfo.title;
        this.elements.trackArtist.textContent = trackInfo.artist;
        this.elements.trackAlbum.textContent = trackInfo.album || '';
        
        // Update page title
        document.title = `${trackInfo.title} - ${trackInfo.artist} | Harmony`;
        
        // Add animation class
        this.playerElement.classList.add('track-changing');
        setTimeout(() => {
            this.playerElement.classList.remove('track-changing');
        }, 500);
    }
    
    updatePlayButton(isPlaying) {
        const icon = this.elements.playPauseBtn.querySelector('i');
        icon.className = isPlaying ? 'fas fa-pause' : 'fas fa-play';
        this.elements.playPauseBtn.title = isPlaying ? 'Pause' : 'Play';
        this.elements.playPauseBtn.setAttribute('aria-label', isPlaying ? 'Pause' : 'Play');
    }
    
    updateProgress() {
        if (!this.duration) return;
        
        const percent = (this.currentTime / this.duration) * 100;
        
        this.elements.progressFill.style.width = `${percent}%`;
        this.elements.progressHandle.style.left = `${percent}%`;
        this.elements.timeCurrent.textContent = this.formatTime(this.currentTime);
        
        // Update progress bar aria attributes
        this.elements.progressBar.setAttribute('aria-valuenow', Math.round(percent));
        this.elements.progressBar.setAttribute('aria-valuetext', `${this.formatTime(this.currentTime)} of ${this.formatTime(this.duration)}`);
    }
    
    updateBuffered() {
        if (!this.audio || !this.duration) return;
        
        const buffered = this.audio.buffered;
        if (buffered.length > 0) {
            const bufferedEnd = buffered.end(buffered.length - 1);
            const bufferedPercent = (bufferedEnd / this.duration) * 100;
            this.elements.progressBuffered.style.width = `${bufferedPercent}%`;
        }
    }
    
    updateDuration() {
        this.elements.timeDuration.textContent = this.formatTime(this.duration);
        
        // Update progress bar aria attributes
        this.elements.progressBar.setAttribute('aria-valuemax', '100');
        this.elements.progressBar.setAttribute('aria-valuemin', '0');
    }
    
    updateVolumeDisplay() {
        const displayVolume = this.isMuted ? 0 : this.volume;
        const percent = displayVolume * 100;
        
        this.elements.volumeFill.style.width = `${percent}%`;
        this.elements.volumeHandle.style.left = `${percent}%`;
        
        // Update volume icon
        const icon = this.elements.volumeBtn.querySelector('i');
        if (this.isMuted || this.volume === 0) {
            icon.className = 'fas fa-volume-mute';
        } else if (this.volume < 0.5) {
            icon.className = 'fas fa-volume-down';
        } else {
            icon.className = 'fas fa-volume-up';
        }
        
        // Update volume slider aria attributes
        this.elements.volumeSlider.setAttribute('aria-valuenow', Math.round(percent));
        this.elements.volumeSlider.setAttribute('aria-valuetext', `${Math.round(percent)}%`);
    }
    
    updateShuffleButton() {
        this.elements.shuffleBtn.classList.toggle('active', this.isShuffled);
        this.elements.shuffleBtn.title = this.isShuffled ? 'Disable Shuffle' : 'Enable Shuffle';
    }
    
    updateRepeatButton() {
        const icon = this.elements.repeatBtn.querySelector('i');
        
        this.elements.repeatBtn.classList.remove('active', 'repeat-one');
        
        switch (this.repeatMode) {
            case 'one':
                this.elements.repeatBtn.classList.add('active', 'repeat-one');
                this.elements.repeatBtn.title = 'Repeat One';
                break;
            case 'all':
                this.elements.repeatBtn.classList.add('active');
                this.elements.repeatBtn.title = 'Repeat All';
                break;
            default:
                this.elements.repeatBtn.title = 'Repeat Off';
                break;
        }
    }
    
    updateLikeButton(isLiked) {
        const icon = this.elements.likeBtn.querySelector('i');
        icon.className = isLiked ? 'fas fa-heart' : 'far fa-heart';
        this.elements.likeBtn.title = isLiked ? 'Unlike' : 'Like';
    }
    
    // Utility Methods
    formatTime(seconds) {
        if (isNaN(seconds) || seconds < 0) return '0:00';
        
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    // Keyboard Handling
    handleKeyboard(event) {
        // Only handle keyboard shortcuts when not typing in an input
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA' || event.target.isContentEditable) {
            return;
        }
        
        switch (event.code) {
            case 'Space':
                event.preventDefault();
                this.togglePlayPause();
                break;
            case 'ArrowLeft':
                event.preventDefault();
                if (event.shiftKey) {
                    this.previousTrack();
                } else if (this.audio) {
                    this.audio.currentTime = Math.max(0, this.audio.currentTime - 10);
                }
                break;
            case 'ArrowRight':
                event.preventDefault();
                if (event.shiftKey) {
                    this.nextTrack();
                } else if (this.audio) {
                    this.audio.currentTime = Math.min(this.duration, this.audio.currentTime + 10);
                }
                break;
            case 'ArrowUp':
                event.preventDefault();
                this.volume = Math.min(1, this.volume + 0.1);
                if (this.audio && !this.isMuted) this.audio.volume = this.volume;
                this.updateVolumeDisplay();
                this.saveSettings();
                break;
            case 'ArrowDown':
                event.preventDefault();
                this.volume = Math.max(0, this.volume - 0.1);
                if (this.audio && !this.isMuted) this.audio.volume = this.volume;
                this.updateVolumeDisplay();
                this.saveSettings();
                break;
            case 'KeyM':
                event.preventDefault();
                this.toggleMute();
                break;
            case 'KeyS':
                event.preventDefault();
                this.toggleShuffle();
                break;
            case 'KeyR':
                event.preventDefault();
                this.toggleRepeat();
                break;
        }
    }
    
    handleProgressKeydown(event) {
        if (!this.audio || !this.duration) return;
        
        let seekAmount = 0;
        
        switch (event.code) {
            case 'ArrowLeft':
                seekAmount = -5;
                break;
            case 'ArrowRight':
                seekAmount = 5;
                break;
            case 'Home':
                this.audio.currentTime = 0;
                return;
            case 'End':
                this.audio.currentTime = this.duration;
                return;
            default:
                return;
        }
        
        event.preventDefault();
        this.audio.currentTime = Math.max(0, Math.min(this.duration, this.audio.currentTime + seekAmount));
    }
    
    handleVolumeKeydown(event) {
        let volumeChange = 0;
        
        switch (event.code) {
            case 'ArrowLeft':
            case 'ArrowDown':
                volumeChange = -0.1;
                break;
            case 'ArrowRight':
            case 'ArrowUp':
                volumeChange = 0.1;
                break;
            case 'Home':
                this.volume = 0;
                break;
            case 'End':
                this.volume = 1;
                break;
            default:
                return;
        }
        
        event.preventDefault();
        
        if (volumeChange !== 0) {
            this.volume = Math.max(0, Math.min(1, this.volume + volumeChange));
        }
        
        if (this.audio && !this.isMuted) {
            this.audio.volume = this.volume;
        }
        
        this.updateVolumeDisplay();
        this.saveSettings();
    }
    
    // Activity Tracking
    async trackPlayActivity() {
        if (!this.currentTrack) return;
        
        try {
            await fetch(`/client/track/${this.currentTrack.id}/play`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ duration: 0 })
            });
        } catch (error) {
            console.error('Error tracking play activity:', error);
        }
    }
    
    // Settings Persistence
    saveSettings() {
        const settings = {
            volume: this.volume,
            isMuted: this.isMuted,
            isShuffled: this.isShuffled,
            repeatMode: this.repeatMode,
            isMinimized: this.isMinimized
        };
        
        try {
            localStorage.setItem('harmonyPlayerSettings', JSON.stringify(settings));
        } catch (error) {
            console.error('Error saving settings:', error);
        }
    }
    
    loadSettings() {
        try {
            const settings = JSON.parse(localStorage.getItem('harmonyPlayerSettings') || '{}');
            
            this.volume = settings.volume ?? 1.0;
            this.isMuted = settings.isMuted ?? false;
            this.isShuffled = settings.isShuffled ?? false;
            this.repeatMode = settings.repeatMode ?? 'none';
            this.isMinimized = settings.isMinimized ?? false;
            
            // Apply settings to audio if it exists
            if (this.audio) {
                this.audio.volume = this.isMuted ? 0 : this.volume;
            }
            
            // Update UI
            this.updateVolumeDisplay();
            this.updateShuffleButton();
            this.updateRepeatButton();
            
            if (this.isMinimized) {
                this.toggleMinimize();
            }
            
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }
    
    // Playlist Management
    setPlaylist(tracks, startIndex = 0) {
        this.playlist = tracks;
        this.currentIndex = startIndex;
        console.log(`Playlist set with ${tracks.length} tracks, starting at index ${startIndex}`);
    }
    
    clearPlaylist() {
        this.playlist = [];
        this.currentIndex = -1;
        console.log('Playlist cleared');
    }
    
    // Preloading for Performance
    async preloadNextTracks() {
        if (this.preloadedTracks.size >= this.maxPreloadedTracks) {
            return;
        }
        
        const tracksToPreload = [];
        
        // Add next track in queue
        if (this.queue.length > 0) {
            tracksToPreload.push(this.queue[0].id);
        }
        
        // Add next track in playlist
        if (this.playlist.length > 0 && this.currentIndex >= 0) {
            const nextIndex = this.currentIndex < this.playlist.length - 1 ? this.currentIndex + 1 : 0;
            tracksToPreload.push(this.playlist[nextIndex].id);
        }
        
        // Preload tracks
        for (const trackId of tracksToPreload) {
            if (!this.preloadedTracks.has(trackId)) {
                try {
                    const trackInfo = await this.fetchTrackInfo(trackId);
                    this.preloadedTracks.set(trackId, trackInfo);
                    console.log(`Preloaded track ${trackId}`);
                    
                    // Limit cache size
                    if (this.preloadedTracks.size > this.maxPreloadedTracks) {
                        const firstKey = this.preloadedTracks.keys().next().value;
                        this.preloadedTracks.delete(firstKey);
                    }
                } catch (error) {
                    console.warn(`Failed to preload track ${trackId}:`, error);
                }
            }
        }
    }
    
    // Media Session API Integration
    setupMediaSession() {
        if ('mediaSession' in navigator) {
            navigator.mediaSession.setActionHandler('play', () => this.play());
            navigator.mediaSession.setActionHandler('pause', () => this.pause());
            navigator.mediaSession.setActionHandler('previoustrack', () => this.previousTrack());
            navigator.mediaSession.setActionHandler('nexttrack', () => this.nextTrack());
            navigator.mediaSession.setActionHandler('seekbackward', () => {
                if (this.audio) this.audio.currentTime = Math.max(0, this.audio.currentTime - 10);
            });
            navigator.mediaSession.setActionHandler('seekforward', () => {
                if (this.audio) this.audio.currentTime = Math.min(this.duration, this.audio.currentTime + 10);
            });
            
            console.log('Media Session API handlers set up');
        }
    }
    
    updateMediaSession() {
        if ('mediaSession' in navigator && this.currentTrack) {
            navigator.mediaSession.metadata = new MediaMetadata({
                title: this.currentTrack.title,
                artist: this.currentTrack.artist,
                album: this.currentTrack.album || '',
                artwork: [
                    { src: '/static/images/default-artwork.png', sizes: '512x512', type: 'image/png' }
                ]
            });
        }
    }
    
    // Performance Monitoring
    startPerformanceMonitoring() {
        // Monitor audio performance
        setInterval(() => {
            if (this.audio && this.isPlaying) {
                const buffered = this.audio.buffered;
                if (buffered.length > 0) {
                    const bufferedEnd = buffered.end(buffered.length - 1);
                    const currentTime = this.audio.currentTime;
                    const bufferHealth = bufferedEnd - currentTime;
                    
                    // Warn if buffer is low
                    if (bufferHealth < 5 && !this.audio.ended) {
                        console.warn('Low buffer health:', bufferHealth);
                    }
                }
            }
        }, 5000);
    }
    
    // Cleanup
    cleanupAudio() {
        if (this.audio) {
            this.audio.pause();
            this.audio.src = '';
            this.audio.load();
            this.audio = null;
        }
    }
    
    cleanup() {
        console.log('Cleaning up audio player...');
        
        // Clean up audio
        this.cleanupAudio();
        
        // Remove event listeners
        for (const [element, listeners] of this.eventListeners) {
            for (const { event, handler } of listeners) {
                element.removeEventListener(event, handler);
            }
        }
        this.eventListeners.clear();
        
        // Clear caches
        this.preloadedTracks.clear();
        
        // Save settings
        this.saveSettings();
    }
    
    // Public API Methods
    getCurrentTrack() {
        return this.currentTrack;
    }
    
    getPlaylist() {
        return this.playlist;
    }
    
    getQueue() {
        return this.queue;
    }
    
    isPlayerPlaying() {
        return this.isPlaying;
    }
    
    getVolume() {
        return this.volume;
    }
    
    getCurrentTime() {
        return this.currentTime;
    }
    
    getDuration() {
        return this.duration;
    }
}

// Initialize player when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.harmonyPlayer = new HarmonyAudioPlayer();
    console.log('Harmony Audio Player ready');
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HarmonyAudioPlayer;
}