import sounddevice as sd
import numpy as np
import torch
from typing import Dict, Any, Optional
from .quantum_harmonic import QuantumHarmonicComposer

class QuantumAudioInterface:
    """Audio interface for quantum harmonic compositions"""
    def __init__(self, config: Dict[str, Any]):
        self.composer = QuantumHarmonicComposer(config)
        self.sample_rate = 44100
        self.channels = 2  # Stereo output
        
    async def play_quantum_harmony(self,
                                 quantum_state: torch.Tensor,
                                 duration: float = 5.0,
                                 base_frequency: float = 440.0):
        """Play quantum harmonic pattern through speakers"""
        # Generate harmonic pattern
        harmony = await self.composer.compose_quantum_harmony(quantum_state)
        pattern = await self.composer.generate_harmonic_pattern(
            base_frequency=base_frequency,
            duration=int(duration)
        )
        
        # Apply quantum resonance
        audio = pattern * harmony["resonance"].unsqueeze(0)
        
        # Convert to stereo
        stereo = torch.stack([audio, audio])
        
        # Normalize and convert to numpy
        audio_data = stereo.numpy()
        audio_data = audio_data / np.max(np.abs(audio_data))
        
        # Play through speakers
        sd.play(audio_data.T, self.sample_rate)
        sd.wait()  # Wait until audio finishes
        
    async def play_quantum_symphony(self,
                                  quantum_states: torch.Tensor,
                                  duration: float = 60.0,
                                  base_frequency: float = 440.0):
        """Play complete quantum symphony through speakers"""
        # Generate symphony
        symphony = await self.composer.compose_symphony(
            quantum_states=quantum_states,
            base_frequency=base_frequency,
            duration=duration
        )
        
        # Convert to stereo
        audio = symphony["symphony"]
        stereo = torch.stack([audio, audio])
        
        # Normalize and convert to numpy
        audio_data = stereo.numpy()
        audio_data = audio_data / np.max(np.abs(audio_data))
        
        # Play through speakers
        sd.play(audio_data.T, self.sample_rate)
        sd.wait()  # Wait until audio finishes
        
    async def save_quantum_symphony(self,
                                  quantum_states: torch.Tensor,
                                  output_file: str,
                                  duration: float = 60.0,
                                  base_frequency: float = 440.0):
        """Save quantum symphony as audio file"""
        from scipy.io import wavfile
        
        # Generate symphony
        symphony = await self.composer.compose_symphony(
            quantum_states=quantum_states,
            base_frequency=base_frequency,
            duration=duration
        )
        
        # Convert to stereo
        audio = symphony["symphony"]
        stereo = torch.stack([audio, audio])
        
        # Normalize and convert to numpy
        audio_data = stereo.numpy()
        audio_data = audio_data / np.max(np.abs(audio_data))
        
        # Save as WAV file
        wavfile.write(
            output_file,
            self.sample_rate,
            (audio_data.T * 32767).astype(np.int16)
        )