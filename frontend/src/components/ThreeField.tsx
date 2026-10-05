import React, { useRef, useState, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { FielderMarker } from './FielderMarker';
import type { FielderPosition } from './TacticalPanel';
import './ThreeField.css';

export interface FieldPlacement {
  position_name: string;
  name?: string;
  x: number;
  y: number;
  role: string;
  reason?: string;
}

export interface ThreeFieldProps {
  fielders: (FieldPlacement | FielderPosition)[];
  onUpdateFielder?: (name: string, x: number, y: number) => void;
  zoneChart?: Record<string, number>;
  venueId?: string;
  pitchType?: string;
  windSpeedKph?: number;
  windAngleDegrees?: number;
}

// 3D Stumps & Bails component
const Stumps3D: React.FC<{ zPosition: number }> = ({ zPosition }) => {
  return (
    <group position={[0, 0, zPosition]}>
      {/* Three Stumps */}
      {[-0.11, 0, 0.11].map((xOffset, i) => (
        <mesh key={i} position={[xOffset, 0.35, 0]}>
          <cylinderGeometry args={[0.018, 0.018, 0.71, 12]} />
          <meshStandardMaterial color="#d4a373" roughness={0.3} metalness={0.1} />
        </mesh>
      ))}
      {/* Bails */}
      <mesh position={[0, 0.71, 0]}>
        <boxGeometry args={[0.26, 0.015, 0.015]} />
        <meshStandardMaterial color="#faedcd" roughness={0.4} />
      </mesh>
    </group>
  );
};

// Mow Stripes Turf component for authentic broadcast match ground
const StadiumTurf: React.FC = () => {
  const stripeRadii = [15, 25, 35, 45, 55, 65, 75];
  return (
    <group>
      {/* Base Outfield Ground */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.015, 0]}>
        <circleGeometry args={[82, 64]} />
        <meshStandardMaterial color="#0f2615" roughness={0.9} />
      </mesh>

      {/* Alternating Cut Mow Stripes */}
      {stripeRadii.map((r, i) => (
        <mesh key={i} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
          <ringGeometry args={[r - 5, r, 64]} />
          <meshStandardMaterial
            color={i % 2 === 0 ? '#13351d' : '#184224'}
            roughness={0.88}
          />
        </mesh>
      ))}
    </group>
  );
};

// 3D Asymmetric Venue Boundary Rope (Lord's, MCG, Eden Park, Wankhede, Adelaide)
const VenueBoundaryRope: React.FC<{ venueId: string }> = ({ venueId }) => {
  const points = useMemo(() => {
    let rStraight = 65.0;
    let rSquareOff = 65.0;
    let rSquareLeg = 65.0;
    let rBehind = 65.0;

    switch (venueId) {
      case 'eden_park':
        rStraight = 55.0;
        rSquareOff = 68.0;
        rSquareLeg = 68.0;
        rBehind = 58.0;
        break;
      case 'lords':
        rStraight = 76.0;
        rSquareOff = 60.0;
        rSquareLeg = 60.0;
        rBehind = 62.0;
        break;
      case 'mcg':
        rStraight = 82.0;
        rSquareOff = 74.0;
        rSquareLeg = 74.0;
        rBehind = 70.0;
        break;
      case 'adelaide':
        rStraight = 80.0;
        rSquareOff = 58.0;
        rSquareLeg = 58.0;
        rBehind = 60.0;
        break;
      case 'wankhede':
        rStraight = 68.0;
        rSquareOff = 62.0;
        rSquareLeg = 62.0;
        rBehind = 60.0;
        break;
      case 'chepauk':
        rStraight = 68.0;
        rSquareOff = 64.0;
        rSquareLeg = 64.0;
        rBehind = 62.0;
        break;
      default:
        rStraight = 65.0;
        rSquareOff = 65.0;
        rSquareLeg = 65.0;
        rBehind = 65.0;
        break;
    }

    const pts: THREE.Vector3[] = [];
    const segments = 128;
    for (let i = 0; i <= segments; i++) {
      const theta = (i / segments) * 2 * Math.PI;
      const sinT = Math.sin(theta);
      const cosT = Math.cos(theta);

      const rx = sinT >= 0 ? rSquareOff : rSquareLeg;
      const ry = cosT >= 0 ? rStraight : rBehind;

      const r = 1.0 / Math.sqrt((sinT * sinT) / (rx * rx) + (cosT * cosT) / (ry * ry));
      const x = r * sinT;
      const z = r * cosT;
      pts.push(new THREE.Vector3(x, 0.02, z));
    }
    return pts;
  }, [venueId]);

  const lineGeometry = useMemo(() => {
    return new THREE.BufferGeometry().setFromPoints(points);
  }, [points]);

  return (
    <group>
      {/* Glowing Neon Line */}
      <primitive object={new THREE.Line(lineGeometry, new THREE.LineBasicMaterial({ color: '#ffffff', linewidth: 2 }))} />
      {/* Outer subtle boundary glow */}
      <primitive object={new THREE.Line(lineGeometry, new THREE.LineBasicMaterial({ color: '#00f3ff', transparent: true, opacity: 0.6, linewidth: 1 }))} position={[0, 0.01, 0]} />
    </group>
  );
};

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

        let color = '#00ff9d'; // Green (suppressed/safe)
        let opacity = 0.12;
        if (val > 1.35) {
          color = '#ff0055'; // Red (hot danger zone)
          opacity = 0.35;
        } else if (val > 0.85) {
          color = '#ffb700'; // Yellow (moderate threat)
          opacity = 0.22;
        }

        const startAngle = d.angle - Math.PI / 8;
        const length = Math.PI / 4;

        return (
          <mesh key={d.name} rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[10, 65, 32, 1, startAngle, length]} />
            <meshBasicMaterial color={color} opacity={opacity} transparent side={THREE.DoubleSide} />
          </mesh>
        );
      })}
    </group>
  );
};

export const ThreeField: React.FC<ThreeFieldProps> = ({
  fielders,
  onUpdateFielder,
  zoneChart,
  venueId = 'lords',
  pitchType = 'green_seam',
  windSpeedKph = 18,
  windAngleDegrees = 45
}) => {
  const controlsRef = useRef<any>(null);
  const [showHeatmap, setShowHeatmap] = useState<boolean>(true);
  const [showCoverage, setShowCoverage] = useState<boolean>(true);

  // Pitch surface color mapping based on selected physics
  const pitchColor = useMemo(() => {
    switch (pitchType) {
      case 'green_seam':
        return '#8a9a5b'; // Lush grassy tint
      case 'dusty_spin':
        return '#d4a373'; // Dry abrasive clay
      case 'flat_highway':
        return '#e2d4b7'; // Hard light highway
      case 'slow_low':
        return '#6f4e37'; // Damp heavy soil
      default:
        return '#c29a6a';
    }
  }, [pitchType]);

  // View Preset Handler
  const handleSetView = (preset: 'top' | 'tactical' | 'batter' | 'bowler') => {
    if (!controlsRef.current) return;
    const controls = controlsRef.current;

    switch (preset) {
      case 'top':
        controls.object.position.set(0, 85, 0.01);
        controls.target.set(0, 0, 0);
        break;
      case 'batter':
        controls.object.position.set(0, 2.2, -16);
        controls.target.set(0, 1.2, 10);
        break;
      case 'bowler':
        controls.object.position.set(0, 2.6, 16);
        controls.target.set(0, 1.2, -10);
        break;
      case 'tactical':
      default:
        controls.object.position.set(0, 48, 62);
        controls.target.set(0, 0, 0);
        break;
    }
    controls.update();
  };

  return (
    <div className="three-field-container">
      {/* Top Floating HUD Toolbar */}
      <div className="view-presets">
        <div className="preset-group">
          <button type="button" onClick={() => handleSetView('tactical')} className="btn btn-preset-ui">
            🛡️ Tactical
          </button>
          <button type="button" onClick={() => handleSetView('top')} className="btn btn-preset-ui">
            🗺️ Top Down
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
            🔥 Heatmap
          </button>
          <button
            type="button"
            onClick={() => setShowCoverage(!showCoverage)}
            className={`btn btn-toggle-ui ${showCoverage ? 'active' : ''}`}
          >
            ⭕ Coverage
          </button>
        </div>
      </div>

      {/* Floating Holographic Wind Compass Widget */}
      <div className="wind-compass-hud">
        <div className="compass-dial">
          <div
            className="compass-arrow"
            style={{ transform: `rotate(${windAngleDegrees}deg)` }}
          >
            ▲
          </div>
        </div>
        <div className="compass-telemetry font-mono">
          <span className="wind-speed">{windSpeedKph} km/h</span>
          <span className="wind-heading">{windAngleDegrees}° DEFLECTION</span>
        </div>
      </div>

      {/* Bottom Spatial HUD Banner */}
      <div className="spatial-hud-footer">
        <span className="hud-badge font-mono">
          🏟️ 3D SPATIAL ARENA · {venueId.toUpperCase()} BOUNDARY · 27.4m INFIELD RING
        </span>
        <span className="hud-hint font-mono">💡 Drag fielder spheres to test live gap vulnerabilities</span>
      </div>

      {/* 3D Canvas */}
      <Canvas
        camera={{ position: [0, 48, 62], fov: 50 }}
        style={{ background: '#04070e' }}
      >
        <ambientLight intensity={0.8} />
        <directionalLight position={[15, 45, 25]} intensity={1.6} castShadow />
        <directionalLight position={[-15, 25, -25]} intensity={0.6} />

        {/* Stadium Grass with Mow Stripes */}
        <StadiumTurf />

        {/* 3D Wagon-Wheel Risk Heatmap Sectors */}
        <ZoneSectors zoneChart={zoneChart} visible={showHeatmap} />

        {/* Pitch Surface (3.05m x 20.12m) with pitch physics color */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
          <planeGeometry args={[3.05, 20.12]} />
          <meshStandardMaterial color={pitchColor} roughness={0.7} />
        </mesh>

        {/* Stumps & Bails at both ends */}
        <Stumps3D zPosition={-10.06} />
        <Stumps3D zPosition={10.06} />

        {/* Crease Markings */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, -8.9]}>
          <planeGeometry args={[2.64, 0.08]} />
          <meshBasicMaterial color="#ffffff" opacity={0.85} transparent />
        </mesh>
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 8.9]}>
          <planeGeometry args={[2.64, 0.08]} />
          <meshBasicMaterial color="#ffffff" opacity={0.85} transparent />
        </mesh>

        {/* 30-Yard Infield Circle (27.4m radius) */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
          <ringGeometry args={[27.25, 27.55, 64]} />
          <meshBasicMaterial color="#ffb700" opacity={0.8} transparent />
        </mesh>

        {/* Asymmetric Venue Boundary Rope */}
        <VenueBoundaryRope venueId={venueId} />

        {/* Fielder Markers with safe name fallback and unique keys */}
        {fielders.map((f, idx) => {
          const displayName = (f as any).position_name || (f as any).name || `Fielder ${idx + 1}`;
          return (
            <FielderMarker
              key={`${displayName}-${idx}`}
              name={displayName}
              x={f.x}
              y={f.y}
              role={f.role as any}
              showCoverage={showCoverage}
              onUpdate={(newX, newY) => onUpdateFielder && onUpdateFielder(displayName, newX, newY)}
            />
          );
        })}

        <OrbitControls
          ref={controlsRef}
          enableDamping
          dampingFactor={0.05}
          maxPolarAngle={Math.PI / 2 - 0.05}
          minDistance={10}
          maxDistance={140}
        />
      </Canvas>
    </div>
  );
};
