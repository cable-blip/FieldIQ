import React, { useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { FielderMarker } from './FielderMarker';
import type { FielderPosition } from './TacticalPanel';
import './ThreeField.css';

interface ThreeFieldProps {
  fielders: FielderPosition[];
  onUpdateFielder: (name: string, x: number, y: number) => void;
  zoneChart?: Record<string, number>;
}

const ZoneSectors: React.FC<{ zoneChart?: Record<string, number>; visible: boolean }> = ({ zoneChart, visible }) => {
  if (!visible || !zoneChart) return null;

  const directions = [
    { name: 'Mid Off', angle: 0 },
    { name: 'Cover', angle: Math.PI / 4 },
    { name: 'Point', angle: Math.PI / 2 },
    { name: 'Third Man', angle: (3 * Math.PI) / 4 },
    { name: 'Fine Leg', angle: Math.PI },
    { name: 'Square Leg', angle: (5 * Math.PI) / 4 },
    { name: 'Mid Wicket', angle: (6 * Math.PI) / 4 },
    { name: 'Mid On', angle: (7 * Math.PI) / 4 },
  ];

  return (
    <group position={[0, 0.015, 0]}>
      {directions.map((d) => {
        const keyDeep = `${d.name}_Deep`;
        const keyMid = `${d.name}_Mid`;
        const keyInner = `${d.name}_Inner`;
        const val = ((zoneChart[keyDeep] || 1.0) + (zoneChart[keyMid] || 1.0) + (zoneChart[keyInner] || 1.0)) / 3;

        let color = '#34c759'; // Green
        let opacity = 0.15;
        if (val > 1.35) {
          color = '#ff3b30'; // Red
          opacity = 0.35;
        } else if (val > 0.85) {
          color = '#ffcc00'; // Yellow
          opacity = 0.25;
        }

        const startAngle = d.angle - Math.PI / 8;
        const length = Math.PI / 4;

        return (
          <mesh key={d.name} rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[10, 65, 16, 1, startAngle, length]} />
            <meshBasicMaterial color={color} opacity={opacity} transparent side={THREE.DoubleSide} />
          </mesh>
        );
      })}
    </group>
  );
};

export const ThreeField: React.FC<ThreeFieldProps> = ({ fielders, onUpdateFielder, zoneChart }) => {
  const controlsRef = useRef<any>(null);
  const [showHeatmap, setShowHeatmap] = useState<boolean>(true);
  const [showCoverage, setShowCoverage] = useState<boolean>(true);

  // View Preset Handler
  const handleSetView = (preset: 'top' | 'tactical' | 'batter' | 'bowler') => {
    if (!controlsRef.current) return;
    const controls = controlsRef.current;

    switch (preset) {
      case 'top':
        controls.object.position.set(0, 80, 0.01);
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
      {/* Viewport Toolbar (Presets + Feature Toggles) */}
      <div className="view-presets">
        <div className="preset-group">
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

        <div className="toggle-group">
          <button
            type="button"
            onClick={() => setShowHeatmap(!showHeatmap)}
            className={`btn btn-toggle-ui ${showHeatmap ? 'active' : ''}`}
          >
            🔥 Risk Heatmap
          </button>
          <button
            type="button"
            onClick={() => setShowCoverage(!showCoverage)}
            className={`btn btn-toggle-ui ${showCoverage ? 'active' : ''}`}
          >
            ⭕ Coverage Radii
          </button>
        </div>
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

        {/* 3D Wagon-Wheel Risk Heatmap Sectors */}
        <ZoneSectors zoneChart={zoneChart} visible={showHeatmap} />

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
            showCoverage={showCoverage}
            onUpdate={(newX, newY) => onUpdateFielder(f.name, newX, newY)}
          />
        ))}

        <OrbitControls
          ref={controlsRef}
          enableDamping
          dampingFactor={0.05}
          maxPolarAngle={Math.PI / 2 - 0.05}
          minDistance={10}
          maxDistance={120}
        />
      </Canvas>
    </div>
  );
};
