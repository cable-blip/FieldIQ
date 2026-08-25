import React, { useRef, useState } from 'react';
import * as THREE from 'three';
import { ThreeEvent } from '@react-three/fiber';

interface FielderMarkerProps {
  name: string;
  x: number;
  y: number;
  role: 'wicket_taking' | 'run_saving' | 'core';
  onUpdate: (x: number, y: number) => void;
}

export const FielderMarker: React.FC<FielderMarkerProps> = ({ name, x, y, role, onUpdate }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState<boolean>(false);
  const [active, setActive] = useState<boolean>(false);

  // Map role to color
  const getColor = () => {
    if (name === 'Wicketkeeper') return '#d4af37'; // Gold
    if (name === 'Bowler') return '#ffffff'; // White
    if (role === 'wicket_taking') return '#ff3b30'; // Red
    return '#007aff'; // Blue
  };

  const color = getColor();

  // Drag handler using R3F pointer events
  const handlePointerDown = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    setActive(true);
  };

  const handlePointerMove = (e: ThreeEvent<PointerEvent>) => {
    if (!active) return;
    e.stopPropagation();
    
    // Find intersection with the invisible ground plane
    // We map 3D X -> field X, 3D Z -> field Y
    const newX = e.unprojectedPoint.x;
    const newY = e.unprojectedPoint.z;

    // Clamp coordinates within the boundary boundary (65m radius)
    const dist = Math.sqrt(newX * newX + newY * newY);
    if (dist <= 65) {
      onUpdate(newX, newY);
    } else {
      // Clamp to boundary rope edge
      const angle = Math.atan2(newY, newX);
      onUpdate(Math.cos(angle) * 65, Math.sin(angle) * 65);
    }
  };

  const handlePointerUp = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    setActive(false);
  };

  return (
    <group>
      {/* Draggable sphere */}
      <mesh
        ref={meshRef}
        position={[x, 0.5, y]} // Height is 0.5 so it sits on the ground
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[1.2, 16, 16]} />
        <meshStandardMaterial
          color={hovered || active ? '#58a6ff' : color}
          roughness={0.4}
          metalness={0.1}
          emissive={active ? '#58a6ff' : '#000000'}
          emissiveIntensity={0.2}
        />
      </mesh>

      {/* Shadow element on the ground */}
      <mesh position={[x, 0.01, y]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0, 1.4]} />
        <meshBasicMaterial color="#000000" opacity={0.3} transparent />
      </mesh>
    </group>
  );
};
