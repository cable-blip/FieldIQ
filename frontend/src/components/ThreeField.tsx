import React, { useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { FielderMarker } from './FielderMarker';
import type { FielderPosition } from './TacticalPanel';
import './ThreeField.css';

interface ThreeFieldProps {
  fielders: FielderPosition[];
  onUpdateFielder: (name: string, x: number, y: number) => void;
}

export const ThreeField: React.FC<ThreeFieldProps> = ({ fielders, onUpdateFielder }) => {
  const controlsRef = useRef<any>(null);

  // View Preset Handler
  const handleSetView = (preset: 'top' | 'tactical' | 'batter' | 'bowler') => {
    if (!controlsRef.current) return;
    const controls = controlsRef.current;
    
    switch (preset) {
      case 'top':
        controls.object.position.set(0, 80, 0.01); // Slightly offset Z to avoid gimbal lock
        controls.target.set(0, 0, 0);
        break;
      case 'batter':
        controls.object.position.set(0, 2, -15);
        controls.target.set(0, 1.5, 10);
        break;
      case 'bowler':
        controls.object.position.set(0, 2.5, 15);
        controls.target.set(0, 1.5, -10);
        break;
      case 'tactical':
      default:
        controls.object.position.set(0, 45, 60);
        controls.target.set(0, 0, 0);
        break;
    }
    controls.update();
  };

  return (
    <div className="three-field-container">
      {/* View Presets Bar */}
      <div className="view-presets">
        <button type="button" onClick={() => handleSetView('top')} className="btn btn-preset-ui">
          🗺️ Top Down
        </button>
        <button type="button" onClick={() => handleSetView('tactical')} className="btn btn-preset-ui">
          🛡️ Tactical View
        </button>
        <button type="button" onClick={() => handleSetView('batter')} className="btn btn-preset-ui">
          👤 Batter POV
        </button>
        <button type="button" onClick={() => handleSetView('bowler')} className="btn btn-preset-ui">
          ⚾ Bowler POV
        </button>
      </div>

      {/* 3D Canvas */}
      <Canvas
        camera={{ position: [0, 45, 60], fov: 50 }}
        style={{ background: '#111' }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[10, 30, 20]} intensity={1.2} castShadow />

        {/* Outfield Grass */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
          <circleGeometry args={[75, 64]} />
          <meshStandardMaterial color="#1b4d22" roughness={0.9} />
        </mesh>

        {/* Pitch (brown rectangle: 3.05m wide, 20.12m long) */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
          <planeGeometry args={[3.05, 20.12]} />
          <meshStandardMaterial color="#c29a6a" roughness={0.6} />
        </mesh>

        {/* 30-yard circle (yellow ring: 27.4m radius) */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
          <ringGeometry args={[27.3, 27.5, 64]} />
          <meshBasicMaterial color="#e3b341" opacity={0.6} transparent />
        </mesh>

        {/* Boundary Rope (white ring: 65m radius) */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
          <ringGeometry args={[64.8, 65.2, 128]} />
          <meshBasicMaterial color="#ffffff" opacity={0.8} transparent />
        </mesh>

        {/* Fielder Markers */}
        {fielders.map((f) => (
          <FielderMarker
            key={f.name}
            name={f.name}
            x={f.x}
            y={f.y}
            role={f.role}
            onUpdate={(newX, newY) => onUpdateFielder(f.name, newX, newY)}
          />
        ))}

        <OrbitControls
          ref={controlsRef}
          enableDamping
          dampingFactor={0.05}
          maxPolarAngle={Math.PI / 2 - 0.05} // Don't go below ground
          minDistance={10}
          maxDistance={120}
        />
      </Canvas>
    </div>
  );
};
