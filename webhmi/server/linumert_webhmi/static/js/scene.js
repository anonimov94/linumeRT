/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT
*/
"use strict";

const $ = (id) => document.getElementById(id);

// Renderer bez zmiany geometrii i wyglądu v1, poza cyklem życia strony.
export function initScene(getState) {
  // Minimalny renderer WebGL 1: kolorowe linie XYZ w widoku izometrycznym.
  const canvas = $("scene");
  const gl = canvas.getContext("webgl", { antialias: false, depth: false, alpha: false });
  if (!gl) { $("glMessage").hidden = false; return; }
  const vertexSource = `attribute vec3 aPosition; attribute vec3 aColor;
    uniform mat4 uMatrix; varying vec3 vColor;
    void main(){gl_Position=uMatrix*vec4(aPosition,1.0);vColor=aColor;gl_PointSize=9.0;}`;
  const fragmentSource = `precision mediump float; varying vec3 vColor;
    void main(){gl_FragColor=vec4(vColor,1.0);}`;
  function shader(type, source) {
    const s = gl.createShader(type);
    gl.shaderSource(s, source); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }
  let program;
  try {
    program = gl.createProgram();
    gl.attachShader(program, shader(gl.VERTEX_SHADER, vertexSource));
    gl.attachShader(program, shader(gl.FRAGMENT_SHADER, fragmentSource));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
  } catch (_) { $("glMessage").hidden = false; return; }
  gl.useProgram(program);
  const positionAttr = gl.getAttribLocation(program, "aPosition");
  const colorAttr = gl.getAttribLocation(program, "aColor");
  const matrixUniform = gl.getUniformLocation(program, "uMatrix");
  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.enableVertexAttribArray(positionAttr);
  gl.enableVertexAttribArray(colorAttr);
  gl.vertexAttribPointer(positionAttr, 3, gl.FLOAT, false, 24, 0);
  gl.vertexAttribPointer(colorAttr, 3, gl.FLOAT, false, 24, 12);
  const vertices = [];
  const push = (a, b, color) => {
    vertices.push(...a, ...color, ...b, ...color);
  };
  for (let i = -10; i <= 10; ++i) {
    const v = i * 10;
    push([v,-100,0],[v,100,0],[.10,.31,.36]);
    push([-100,v,0],[100,v,0],[.10,.31,.36]);
  }
  push([-100,0,0],[100,0,0],[.18,.9,.9]);
  push([0,-100,0],[0,100,0],[.18,.9,.9]);
  push([0,0,0],[0,0,100],[.97,.73,.31]);
  const staticData = vertices.slice();
  // Widok izometryczny: X,Y -> ekran; Z pionowo, skalowanie współrzędnych.
  const projection = new Float32Array([
     .006,-.0035,0,0,
    -.006,-.0035,0,0,
     0,.009,0,0,
     0,-.08,0,1
  ]);
  function frame() {
    if (canvas.clientWidth === 0 || canvas.clientHeight === 0) return;
    const width = Math.min(canvas.clientWidth * Math.min(devicePixelRatio || 1, 2), 1600);
    const height = Math.min(canvas.clientHeight * Math.min(devicePixelRatio || 1, 2), 1000);
    if (canvas.width !== Math.floor(width) || canvas.height !== Math.floor(height)) {
      canvas.width = Math.floor(width); canvas.height = Math.floor(height);
    }
    const aspect = canvas.width / canvas.height;
    const matrix = projection.slice();
    matrix[0] /= Math.max(1, aspect); matrix[4] /= Math.max(1, aspect);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(.025,.06,.09,1); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniformMatrix4fv(matrixUniform, false, matrix);
    const axes = Object.fromEntries((getState()?.axes || []).map(a => [a.name, a]));
    const coords = ["X","Y","Z"].map(a => Number(axes[a]?.work_position) || 0);
    const [x,y,z] = coords.map(v => Math.max(-100, Math.min(100, v)));
    const data = [...staticData];
    const marker = (a,b) => data.push(...a,1,.76,.27,...b,1,.76,.27);
    marker([x-4,y,z],[x+4,y,z]); marker([x,y-4,z],[x,y+4,z]);
    marker([x,y,z-4],[x,y,z+4]);
    marker([x,y,0],[x,y,z]);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(data), gl.DYNAMIC_DRAW);
    gl.drawArrays(gl.LINES, 0, data.length / 6);
  }
  let lastFrame = 0;
  function animate(timestamp) {
    if (timestamp - lastFrame >= 1000 / 30) {
      lastFrame = timestamp;
      if (!document.hidden) frame();
    }
    requestAnimationFrame(animate);
  }
  requestAnimationFrame(animate);
}
