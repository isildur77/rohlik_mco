/**
 * Rohlik Voice Card - Lovelace card for voice shopping on Rohlik.cz
 * 
 * Usage in Lovelace:
 * type: custom:rohlik-voice-card
 * show_cart: true
 * show_transcript: true
 */

class RohlikVoiceCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = null;
    this._ws = null;
    this._mediaRecorder = null;
    this._audioContext = null;
    this._isRecording = false;
    this._isConnected = false;
    this._transcript = '';
    this._cartItems = [];
    this._audioQueue = [];
    this._isPlaying = false;
  }

  static get properties() {
    return {
      _config: {},
      _hass: {},
    };
  }

  setConfig(config) {
    this._config = {
      show_cart: true,
      show_transcript: true,
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._updateCart();
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          padding: 16px;
        }
        
        .card {
          background: var(--ha-card-background, var(--card-background-color, white));
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow, none);
          padding: 24px;
        }
        
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 20px;
        }
        
        .title {
          font-size: 1.5em;
          font-weight: 500;
          color: var(--primary-text-color);
        }
        
        .logo {
          width: 80px;
          height: auto;
        }
        
        .mic-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          margin: 30px 0;
        }
        
        .mic-button {
          width: 120px;
          height: 120px;
          border-radius: 50%;
          border: none;
          background: linear-gradient(135deg, #4CAF50, #45a049);
          color: white;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
          box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4);
        }
        
        .mic-button:hover {
          transform: scale(1.05);
          box-shadow: 0 6px 20px rgba(76, 175, 80, 0.5);
        }
        
        .mic-button.recording {
          background: linear-gradient(135deg, #f44336, #e53935);
          animation: pulse 1.5s infinite;
          box-shadow: 0 4px 15px rgba(244, 67, 54, 0.4);
        }
        
        .mic-button.connecting {
          background: linear-gradient(135deg, #ff9800, #f57c00);
        }
        
        .mic-button svg {
          width: 48px;
          height: 48px;
        }
        
        @keyframes pulse {
          0% { transform: scale(1); }
          50% { transform: scale(1.05); }
          100% { transform: scale(1); }
        }
        
        .status {
          margin-top: 16px;
          font-size: 0.9em;
          color: var(--secondary-text-color);
          text-align: center;
        }
        
        .transcript {
          background: var(--secondary-background-color);
          border-radius: 8px;
          padding: 16px;
          margin-top: 20px;
          min-height: 60px;
          max-height: 200px;
          overflow-y: auto;
        }
        
        .transcript-label {
          font-size: 0.8em;
          color: var(--secondary-text-color);
          margin-bottom: 8px;
        }
        
        .transcript-text {
          color: var(--primary-text-color);
          line-height: 1.5;
        }
        
        .cart {
          margin-top: 20px;
          border-top: 1px solid var(--divider-color);
          padding-top: 16px;
        }
        
        .cart-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        
        .cart-title {
          font-weight: 500;
          color: var(--primary-text-color);
        }
        
        .cart-total {
          font-weight: bold;
          color: var(--primary-color);
        }
        
        .cart-items {
          font-size: 0.9em;
          color: var(--secondary-text-color);
        }
        
        .cart-link {
          display: inline-block;
          margin-top: 12px;
          padding: 8px 16px;
          background: var(--primary-color);
          color: white;
          text-decoration: none;
          border-radius: 20px;
          font-size: 0.9em;
        }
        
        .cart-link:hover {
          opacity: 0.9;
        }
        
        .waveform {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 40px;
          gap: 3px;
          margin-top: 16px;
        }
        
        .waveform-bar {
          width: 4px;
          background: var(--primary-color);
          border-radius: 2px;
          animation: wave 0.5s ease-in-out infinite;
        }
        
        .waveform-bar:nth-child(1) { animation-delay: 0s; }
        .waveform-bar:nth-child(2) { animation-delay: 0.1s; }
        .waveform-bar:nth-child(3) { animation-delay: 0.2s; }
        .waveform-bar:nth-child(4) { animation-delay: 0.3s; }
        .waveform-bar:nth-child(5) { animation-delay: 0.4s; }
        
        @keyframes wave {
          0%, 100% { height: 10px; }
          50% { height: 30px; }
        }
        
        .hidden {
          display: none;
        }
      </style>
      
      <ha-card>
        <div class="card">
          <div class="header">
            <span class="title">Rohlik Voice</span>
            <svg class="logo" viewBox="0 0 100 40" fill="none">
              <text x="0" y="30" font-family="Arial" font-size="24" font-weight="bold" fill="#4CAF50">Rohlik</text>
            </svg>
          </div>
          
          <div class="mic-container">
            <button class="mic-button" id="micButton">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
              </svg>
            </button>
            
            <div class="waveform hidden" id="waveform">
              <div class="waveform-bar"></div>
              <div class="waveform-bar"></div>
              <div class="waveform-bar"></div>
              <div class="waveform-bar"></div>
              <div class="waveform-bar"></div>
            </div>
            
            <div class="status" id="status">Klikněte pro zahájení nahrávání</div>
          </div>
          
          <div class="transcript ${this._config.show_transcript ? '' : 'hidden'}" id="transcriptContainer">
            <div class="transcript-label">Přepis konverzace:</div>
            <div class="transcript-text" id="transcript">-</div>
          </div>
          
          <div class="cart ${this._config.show_cart ? '' : 'hidden'}" id="cartContainer">
            <div class="cart-header">
              <span class="cart-title">Košík</span>
              <span class="cart-total" id="cartTotal">0 Kč</span>
            </div>
            <div class="cart-items" id="cartItems">Načítání...</div>
            <a href="https://www.rohlik.cz/objednavka/kosik" target="_blank" class="cart-link">
              Otevřít košík na Rohlíku
            </a>
          </div>
        </div>
      </ha-card>
    `;

    this._setupEventListeners();
  }

  _setupEventListeners() {
    const micButton = this.shadowRoot.getElementById('micButton');
    
    // Touch events for mobile/tablet
    micButton.addEventListener('touchstart', (e) => {
      e.preventDefault();
      this._startRecording();
    });
    
    micButton.addEventListener('touchend', (e) => {
      e.preventDefault();
      this._stopRecording();
    });
    
    // Mouse events for desktop
    micButton.addEventListener('mousedown', () => this._startRecording());
    micButton.addEventListener('mouseup', () => this._stopRecording());
    micButton.addEventListener('mouseleave', () => {
      if (this._isRecording) {
        this._stopRecording();
      }
    });
  }

  async _startRecording() {
    if (this._isRecording) return;
    
    const micButton = this.shadowRoot.getElementById('micButton');
    const status = this.shadowRoot.getElementById('status');
    const waveform = this.shadowRoot.getElementById('waveform');
    
    try {
      // Connect to WebSocket if not connected
      if (!this._isConnected) {
        micButton.classList.add('connecting');
        status.textContent = 'Připojování...';
        
        await this._connectWebSocket();
      }
      
      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 24000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        }
      });
      
      // Create AudioContext for processing
      this._audioContext = new AudioContext({ sampleRate: 24000 });
      const source = this._audioContext.createMediaStreamSource(stream);
      const processor = this._audioContext.createScriptProcessor(4096, 1, 1);
      
      processor.onaudioprocess = (e) => {
        if (this._isRecording && this._ws && this._ws.readyState === WebSocket.OPEN) {
          const inputData = e.inputBuffer.getChannelData(0);
          // Convert to 16-bit PCM
          const pcmData = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
          }
          this._ws.send(pcmData.buffer);
        }
      };
      
      source.connect(processor);
      processor.connect(this._audioContext.destination);
      
      this._stream = stream;
      this._processor = processor;
      this._isRecording = true;
      
      micButton.classList.remove('connecting');
      micButton.classList.add('recording');
      waveform.classList.remove('hidden');
      status.textContent = 'Nahrávám... Pusťte pro odeslání';
      
    } catch (err) {
      console.error('Recording error:', err);
      status.textContent = 'Chyba: ' + err.message;
      micButton.classList.remove('connecting', 'recording');
    }
  }

  async _stopRecording() {
    if (!this._isRecording) return;
    
    const micButton = this.shadowRoot.getElementById('micButton');
    const status = this.shadowRoot.getElementById('status');
    const waveform = this.shadowRoot.getElementById('waveform');
    
    this._isRecording = false;
    micButton.classList.remove('recording');
    waveform.classList.add('hidden');
    status.textContent = 'Zpracovávám...';
    
    // Stop audio processing
    if (this._processor) {
      this._processor.disconnect();
      this._processor = null;
    }
    
    if (this._stream) {
      this._stream.getTracks().forEach(track => track.stop());
      this._stream = null;
    }
    
    if (this._audioContext) {
      await this._audioContext.close();
      this._audioContext = null;
    }
    
    // Tell server we're done sending audio
    if (this._ws && this._ws.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify({ type: 'audio_commit' }));
    }
  }

  async _connectWebSocket() {
    return new Promise((resolve, reject) => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      // Add authentication token to WebSocket URL
      const token = this._hass?.auth?.data?.access_token || '';
      const wsUrl = `${protocol}//${window.location.host}/api/rohlik_voice/ws?token=${token}`;
      
      this._ws = new WebSocket(wsUrl);
      this._ws.binaryType = 'arraybuffer';
      
      this._ws.onopen = () => {
        console.log('WebSocket connected');
      };
      
      this._ws.onmessage = async (event) => {
        if (event.data instanceof ArrayBuffer) {
          // Audio data - queue for playback
          this._audioQueue.push(event.data);
          this._playAudioQueue();
        } else {
          // JSON message
          const data = JSON.parse(event.data);
          
          if (data.type === 'connected') {
            this._isConnected = true;
            resolve();
          } else if (data.type === 'transcript') {
            this._updateTranscript(data.text);
          } else if (data.type === 'error') {
            console.error('Server error:', data.message);
            this.shadowRoot.getElementById('status').textContent = 'Chyba: ' + data.message;
            reject(new Error(data.message));
          }
        }
      };
      
      this._ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this._isConnected = false;
        reject(error);
      };
      
      this._ws.onclose = () => {
        console.log('WebSocket closed');
        this._isConnected = false;
        this.shadowRoot.getElementById('status').textContent = 'Odpojeno. Klikněte pro připojení.';
      };
      
      // Timeout
      setTimeout(() => {
        if (!this._isConnected) {
          reject(new Error('Connection timeout'));
        }
      }, 10000);
    });
  }

  async _playAudioQueue() {
    if (this._isPlaying || this._audioQueue.length === 0) return;
    
    this._isPlaying = true;
    const status = this.shadowRoot.getElementById('status');
    status.textContent = 'Přehrávám odpověď...';
    
    try {
      const audioContext = new AudioContext({ sampleRate: 24000 });
      
      while (this._audioQueue.length > 0) {
        const audioData = this._audioQueue.shift();
        const pcmData = new Int16Array(audioData);
        const floatData = new Float32Array(pcmData.length);
        
        for (let i = 0; i < pcmData.length; i++) {
          floatData[i] = pcmData[i] / 32768;
        }
        
        const audioBuffer = audioContext.createBuffer(1, floatData.length, 24000);
        audioBuffer.getChannelData(0).set(floatData);
        
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        source.start();
        
        // Wait for playback to complete
        await new Promise(resolve => {
          source.onended = resolve;
        });
      }
      
      await audioContext.close();
      
    } catch (err) {
      console.error('Audio playback error:', err);
    }
    
    this._isPlaying = false;
    this.shadowRoot.getElementById('status').textContent = 'Klikněte pro nahrávání';
    
    // Refresh cart after response
    this._updateCart();
  }

  _updateTranscript(text) {
    this._transcript += text;
    const transcriptEl = this.shadowRoot.getElementById('transcript');
    if (transcriptEl) {
      transcriptEl.textContent = this._transcript;
      transcriptEl.scrollTop = transcriptEl.scrollHeight;
    }
  }

  async _updateCart() {
    if (!this._hass || !this._config.show_cart) return;
    
    try {
      const result = await this._hass.callWS({
        type: 'rohlik_voice/get_cart',
      });
      
      const cartItems = this.shadowRoot.getElementById('cartItems');
      const cartTotal = this.shadowRoot.getElementById('cartTotal');
      
      if (result && result.content) {
        // Parse cart content
        const content = result.content[0]?.text || 'Košík je prázdný';
        cartItems.textContent = content;
        
        // Extract total if present (simplified)
        const totalMatch = content.match(/(\d+(?:[,.]\d+)?)\s*Kč/);
        if (totalMatch) {
          cartTotal.textContent = totalMatch[0];
        }
      }
    } catch (err) {
      console.log('Cart update skipped:', err.message);
    }
  }

  getCardSize() {
    return 4;
  }
}

customElements.define('rohlik-voice-card', RohlikVoiceCard);

// Register card
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'rohlik-voice-card',
  name: 'Rohlik Voice Card',
  description: 'Voice-controlled shopping on Rohlik.cz',
  preview: true,
});
