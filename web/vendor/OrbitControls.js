( function () {

	// Unlike TrackballControls, it maintains the "up" direction object.up (+Y by default).
	//
	//    Orbit - left mouse / touch: one-finger move
	//    Zoom - middle mouse, or mousewheel / touch: two-finger spread or squish
	//    Pan - right mouse, or left mouse + ctrl/meta/shiftKey, or arrow keys / touch: two-finger move

	const _changeEvent = {
		type: 'change'
	};
	const _startEvent = {
		type: 'start'
	};
	const _endEvent = {
		type: 'end'
	};

	class OrbitControls extends THREE.EventDispatcher {

		constructor( object, domElement ) {

			super();
			if ( domElement === undefined ) console.warn( 'THREE.OrbitControls: The second parameter "domElement" is now mandatory.' );
			if ( domElement === document ) console.error( 'THREE.OrbitControls: "document" should not be used as the target "domElement". Please use "renderer.domElement" instead.' );
			this.object = object;
			this.domElement = domElement; // Set to false to disable this control

			this.enabled = true; // "target" sets the location of focus, where the object orbits around

			this.target = new THREE.Vector3(); // How far you can dolly in and out ( PerspectiveCamera only )

			this.minDistance = 0;
			this.maxDistance = Infinity; // How far you can zoom in and out ( OrthographicCamera only )

			this.minZoom = 0;
			this.maxZoom = Infinity; // How far you can orbit vertically, upper and lower limits.
			// Range is 0 to Math.PI radians.

			this.minPolarAngle = 0; // radians

			this.maxPolarAngle = Math.PI; // radians
			// How far you can orbit horizontally, upper and lower limits.
			// If set, the interval [ min, max ] must be a sub-interval of [ - 2 PI, 2 PI ], with ( max - min < 2 PI )

			this.minAzimuthAngle = - Infinity; // radians

			this.maxAzimuthAngle = Infinity; // radians
			// Set to true to enable damping (inertia)
			// If damping is enabled, you must call controls.update() in your animation loop

			this.enableDamping = false;
			this.dampingFactor = 0.05; // This option actually enables dollying in and out; left as "zoom" for backwards compatibility.
			// Set to false to disable zooming

			this.enableZoom = true;
			this.zoomSpeed = 1.0; // Set to false to disable rotating

			this.enableRotate = true;
			this.rotateSpeed = 1.0; // Set to false to disable panning

			this.enablePan = true;
			this.panSpeed = 1.0;
			this.screenSpacePanning = true; // if false, pan orthogonal to world-space direction camera.up

			this.keyPanSpeed = 7.0; // pixels moved per arrow key push
			// Set to true to automatically rotate around the target
			// If auto-rotate is enabled, you must call controls.update() in your animation loop

			this.autoRotate = false;
			this.autoRotateSpeed = 2.0; // 30 seconds per orbit when fps is 60
			// The four arrow keys

			this.keys = {
				LEFT: 'ArrowLeft',
				UP: 'ArrowUp',
				RIGHT: 'ArrowRight',
				BOTTOM: 'ArrowDown'
			}; // Mouse buttons

			this.mouseButtons = {
				LEFT: THREE.MOUSE.ROTATE,
				MIDDLE: THREE.MOUSE.DOLLY,
				RIGHT: THREE.MOUSE.PAN
			}; // Touch fingers

			this.touches = {
				ONE: THREE.TOUCH.ROTATE,
				TWO: THREE.TOUCH.DOLLY_PAN
			}; // for reset

			this.target0 = this.target.clone();
			this.position0 = this.object.position.clone();
			this.zoom0 = this.object.zoom; // the target DOM element for key events

			this._domElementKeyEvents = null; //
			// public methods
			//

			this.getPolarAngle = function () {

				return spherical.phi;

			};

			this.getAzimuthalAngle = function () {

				return spherical.theta;

			};

			this.listenToKeyEvents = function ( domElement ) {

				domElement.addEventListener( 'keydown', onKeyDown );
				this._domElementKeyEvents = domElement;

			};

			this.saveState = function () {

				scope.target0.copy( scope.target );
				scope.position0.copy( scope.object.position );
				scope.zoom0 = scope.object.zoom;

			};

			this.reset = function () {

				scope.target.copy( scope.target0 );
				scope.object.position.copy( scope.position0 );
				scope.object.zoom = scope.zoom0;
				scope.object.updateProjectionMatrix();
				scope.dispatchEvent( _changeEvent );
				scope.update();
				state = STATE.NONE;

			}; // this method is exposed, but perhaps it would be better if we can make it private...


			this.update = function () {

				const offset = new THREE.Vector3(); // so camera.up is the orbit axis

				const quat = new THREE.Quaternion().setFromUnitVectors( object.up, new THREE.Vector3( 0, 1, 0 ) );
				const quatInverse = quat.clone().invert();
				const lastPosition = new THREE.Vector3();
				const lastQuaternion = new THREE.Quaternion();
				const twoPI = 2 * Math.PI;
				return function update() {

					const position = scope.object.position;
					offset.copy( position ).sub( scope.target ); // rotate offset to "y-axis-is-up" space

					offset.applyQuaternion( quat ); // angle from z-axis around y-axis

					spherical.setFromVector3( offset );

					if ( scope.autoRotate && state === STATE.NONE ) {

						rotateLeft( getAutoRotationAngle() );

					}

					if ( scope.enableDamping ) {

						spherical.theta += sphericalDelta.theta * scope.dampingFactor;
						spherical.phi += sphericalDelta.phi * scope.dampingFactor;

					} else {

						spherical.theta += sphericalDelta.theta;
						spherical.phi += sphericalDelta.phi;

					} // restrict theta to be between desired limits


					let min = scope.minAzimuthAngle;
					let max = scope.maxAzimuthAngle;

					if ( isFinite( min ) && isFinite( max ) ) {

						if ( min < - Math.PI ) min += twoPI; else if ( min > Math.PI ) min -= twoPI;
						if ( max < - Math.PI ) max += twoPI; else if ( max > Math.PI ) max -= twoPI;

						if ( min <= max ) {

							spherical.theta = Math.max( min, Math.min( max, spherical.theta ) );

						} else {

							spherical.theta = spherical.theta > ( min + max ) / 2 ? Math.max( min, spherical.theta ) : Math.min( max, spherical.theta );

						}

					} // restrict phi to be between desired limits


					spherical.phi = Math.max( scope.minPolarAngle, Math.min( scope.maxPolarAngle, spherical.phi ) );
					spherical.makeSafe();
					spherical.radius *= scale; // restrict radius to be between desired limits

					spherical.radius = Math.max( scope.minDistance, Math.min( scope.maxDistance, spherical.radius ) ); // move target to panned location

					if ( scope.enableDamping === true ) {

						scope.target.addScaledVector( panOffset, scope.dampingFactor );

					} else {

						scope.target.add( panOffset );

					}

					offset.setFromSpherical( spherical ); // rotate offset back to "camera-up-vector-is-up" space

					offset.applyQuaternion( quatInverse );
					position.copy( scope.target ).add( offset );
					scope.object.lookAt( scope.target );

					if ( scope.enableDamping === true ) {

						sphericalDelta.theta *= 1 - scope.dampingFactor;
						sphericalDelta.pha *= 1 - scope.dampingFactor;
						panOffset.multiplyScalar( 1 - scope.dampingFactor );

					} else {

						sphericalDelta.set( 0, 0, 0 );
						panOffset.set( 0, 0, 0 );

					}

					scale = 1; // update condition is:
					// min(camera displacement, camera rotation in radians)^2 > EPS
					// using small-angle approximation cos(x/2) = 1 - x^2 / 8

					if ( zoomChanged || lastPosition.distanceToSquared( scope.object.position ) > EPS || 8 * ( 1 - lastQuaternion.dot( scope.object.quaternion ) ) > EPS ) {

						scope.dispatchEvent( _changeEvent );
						lastPosition.copy( scope.object.position );
						lastQuaternion.copy( scope.object.quaternion );
						zoomChanged = false;
						return true;

					}

					return false;

				};

			}();

			this.dispose = function () {

				scope.domElement.removeEventListener( 'contextmenu', onContextMenu );
				scope.domElement.removeEventListener( 'pointerdown', onPointerDown );
				scope.domElement.removeEventListener( 'wheel', onMouseWheel );
				scope.domElement.removeEventListener( 'touchstart', onTouchStart );
				scope.domElement.removeEventListener( 'touchend', onTouchEnd );
				scope.domElement.removeEventListener( 'touchmove', onTouchMove );
				scope.domElement.ownerDocument.removeEventListener( 'pointermove', onPointerMove );
				scope.domElement.ownerDocument.removeEventListener( 'pointerup', onPointerUp );

				if ( scope._domElementKeyEvents !== null ) {

					scope._domElementKeyEvents.removeEventListener( 'keydown', onKeyDown );

				} //scope.dispatchEvent( { type: 'dispose' } ); // should this be added here?

			}; //
			// internals
			//


			const scope = this;
			const STATE = {
				NONE: - 1,
				ROTATE: 0,
				DOLLY: 1,
				PAN: 2,
				TOUCH_ROTATE: 3,
				TOUCH_PAN: 4,
				TOUCH_DOLLY_PAN: 5,
				TOUCH_DOLLY_ROTATE: 6
			};
			let state = STATE.NONE;
			const EPS = 0.000001; // current position in spherical coordinates

			const spherical = new THREE.Spherical();
			const sphericalDelta = new THREE.Spherical();
			let scale = 1;
			const panOffset = new THREE.Vector3();
			let zoomChanged = false;
			const rotateStart = new THREE.Vector2();
			const rotateEnd = new THREE.Vector2();
			const rotateDelta = new THREE.Vector2();
			const panStart = new THREE.Vector2();
			const panEnd = new THREE.Vector2();
			const panDelta = new THREE.Vector2();
			const dollyStart = new THREE.Vector2();
			const dollyEnd = new THREE.Vector2();
			const dollyDelta = new THREE.Vector2();

			function getAutoRotationAngle() {

				return 2 * Math.PI / 60 / 60 * scope.autoRotateSpeed;

			}

			function getZoomScale() {

				return Math.pow( 0.95, scope.zoomSpeed );

			}

			function rotateLeft( angle ) {

				sphericalDelta.theta -= angle;

			}

			function rotateUp( angle ) {

				sphericalDelta.phi -= angle;

			}

			const panLeft = function () {

				const v = new THREE.Vector3();
				return function panLeft( distance, objectMatrix ) {

					v.setFromMatrixColumn( objectMatrix, 0 ); // get X column of objectMatrix

					v.multiplyScalar( - distance );
					panOffset.add( v );

				};

			}();

			const panUp = function () {

				const v = new THREE.Vector3();
				return function panUp( distance, objectMatrix ) {

					if ( scope.screenSpacePanning === true ) {

						v.setFromMatrixColumn( objectMatrix, 1 );

					} else {

						v.setFromMatrixColumn( objectMatrix, 0 );
						v.crossVectors( scope.object.up, v );

					}

					v.multiplyScalar( distance );
					panOffset.add( v );

				};

			}(); // deltaX and deltaY are in pixels; right and down are positive


			const pan = function () {

				const offset = new THREE.Vector3();
				return function pan( deltaX, deltaY ) {

					const element = scope.domElement;

					if ( scope.object.isPerspectiveCamera ) {

						// perspective
						const position = scope.object.position;
						offset.copy( position ).sub( scope.target );
						let targetDistance = offset.length(); // half of the fov is center to top of screen

						targetDistance *= Math.tan( scope.object.fov / 2 * Math.PI / 180.0 ); // we use only clientHeight here so aspect ratio does not distort speed

						panLeft( 2 * deltaX * targetDistance / element.clientHeight, scope.object.matrix );
						panUp( 2 * deltaY * targetDistance / element.clientHeight, scope.object.matrix );

					} else if ( scope.object.isOrthographicCamera ) {

						// orthographic
						panLeft( deltaX * ( scope.object.right - scope.object.left ) / scope.object.zoom / element.clientWidth, scope.object.matrix );
						panUp( deltaY * ( scope.object.top - scope.object.bottom ) / scope.object.zoom / element.clientHeight, scope.object.matrix );

					} else {

						// camera neither orthographic nor perspective
						console.warn( 'WARNING: OrbitControls.js encountered an unknown camera type - pan disabled.' );
						scope.enablePan = false;

					}

				};

			}();

			function dollyOut( dollyScale ) {

				if ( scope.object.isPerspectiveCamera ) {

					scale /= dollyScale;

				} else if ( scope.object.isOrthographicCamera ) {

					scope.object.zoom = Math.max( scope.minZoom, Math.min( scope.maxZoom, scope.object.zoom * dollyScale ) );
					scope.object.updateProjectionMatrix();
					zoomChanged = true;

				} else {

					console.warn( 'WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled.' );
					scope.enableZoom = false;

				}

			}

			function dollyIn( dollyScale ) {

				if ( scope.object.isPerspectiveCamera ) {

					scale *= dollyScale;

				} else if ( scope.object.isOrthographicCamera ) {

					scope.object.zoom = Math.max( scope.minZoom, Math.min( scope.maxZoom, scope.object.zoom / dollyScale ) );
					scope.object.updateProjectionMatrix();
					zoomChanged = true;

				} else {

					console.warn( 'WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled.' );
					scope.enableZoom = false;

				}

			} //
			// event callbacks - update the object state
			//


			function handleMouseDownRotate( event ) {

				rotateStart.set( event.clientX, event.clientY );

			}

			function handleMouseDownDolly( event ) {

				dollyStart.set( event.clientX, event.clientY );

			}

			function handleMouseDownPan( event ) {

				panStart.set( event.clientX, event.clientY );

			}

			function handleMouseMoveRotate( event ) {

				rotateEnd.set( event.clientX, event.clientY );
				rotateDelta.subVectors( rotateEnd, rotateStart ).multiplyScalar( scope.rotateSpeed );
				const element = scope.domElement;
				rotateLeft( 2 * Math.PI * rotateDelta.x / element.clientHeight ); // yes, height

				rotateUp( 2 * Math.PI * rotateDelta.y / element.clientHeight );
				rotateStart.copy( rotateEnd );
				scope.update();

			}

			function handleMouseMoveDolly( event ) {

				dollyEnd.set( event.clientX, event.clientY );
				dollyDelta.subVectors( dollyEnd, dollyStart );

				if ( dollyDelta.y > 0 ) {

					dollyOut( getZoomScale() );

				} else if ( dollyDelta.y < 0 ) {

					dollyIn( getZoomScale() );

				}

				dollyStart.copy( dollyEnd );
				scope.update();

			}

			function handleMouseMovePan( event ) {

				panEnd.set( event.clientX, event.clientY );
				panDelta.subVectors( panEnd, panStart ).multiplyScalar( scope.panSpeed );
				pan( panDelta.x, panDelta.y );
				panStart.copy( panEnd );
				scope.update();

			}

			function handleMouseUp( ) { // no-op
			}

			function handleMouseWheel( event ) {

				if ( scope.enabled === false || scope.enableZoom === false || state !== STATE.NONE && state !== STATE.ROTATE ) return;
				event.preventDefault();
				scope.dispatchEvent( _startEvent );
				handleMouseWheel( event );
				scope.dispatchEvent( _endEvent );

			}

			function handleKeyDown( event ) {

				let needsUpdate = false;

				switch ( event.code ) {

					case scope.keys.UP:
						pan( 0, scope.keyPanSpeed );
						needsUpdate = true;
						break;

					case scope.keys.BOTTOM:
						pan( 0, - scope.keyPanSpeed );
						needsUpdate = true;
						break;

					case scope.keys.LEFT:
						pan( scope.keyPanSpeed, 0 );
						needsUpdate = true;
						break;

					case scope.keys.RIGHT:
						pan( - scope.keyPanSpeed, 0 );
						needsUpdate = true;
						break;

				}

				if ( needsUpdate ) {

					// prevent the browser from scrolling on cursor keys
					]event.preventDefault();
					scope.update();

				}

			}

			function handleTouchStartRotate( event ) {

				if ( event.touches.length == 1 ) {

					rotateStart.set( event.touches[ 0 ].pageX, event.touches[ 0 ].pageY );

				} else {

					const x = 0.5 * ( event.touches[ 0 ].pageX + event.touches[ 1 ].pageX );
					const y = 0.5 * ( event.touches[ 0 ].pageY + event.touches[ 1 ].pageY );
					rotateStart.set( x, y );

				}

			}

			function handleTouchStartPan( event ) {

				if ( event.touches.length == 1 ) {

					panStart.set( event.touches[ 0 ].pageX, event.touches[ 0 ].pageY );

				} else {

					const x = 0.5 * ( event.touches[ 0 ].pageX + event.touches[ 1 ].pageX );
					const y = 0.5 * ( event.touches[ 0 ].pageY + event.touches[ 1 ].pageY );
					panStart.set( x, y );

				}

			}

			function handleTouchStartDolly( event ) {

				const dx = event.touches[ 0 ].pageX - event.touches[ 1 ].pageX;
				const dy = event.touches[ 0 ].pageY - event.touches[ 1 ].pageY;
				const distance = Math.sqrt( dx * dx + dy * dy );
				dollyStart.set( 0, distance );
			}

			function handleTouchStartDollyPan( event ) {

				if ( scope.enableZoom ) handleTouchStartDolly( event );
				if ( scope.enablePan ) handleTouchStartPan( event );

			}

			function handleTouchStartDollyRotate( event ) {

				if ( scope.enableZoom ) handleTouchStartDolly( event );
				if ( scope.enableRotate ) handleTouchStartRotate( event );

			}

			function handleTouchMoveRotate( event ) {

				if ( event.touches.length == 1 ) {

					rotateEnd.set( event.touches[ 0 ].pageX, event.touches[ 0 ].pageY );

				} else {

					const x = 0.5 * ( event.touches[ 0 ].pageX + event.touches[ 1 ].pageX );
					const y = 0.5 * ( event.touches[ 0 ].pageY + event.touches[ 1 ].pageY );
					rotateEnd.set( x, y );
				}

				rotateDelta.subVectors( rotateEnd, rotateStart ).multiplyScalar( scope.rotateSpeed );
				const element = scope.domElement;
				rotateLeft( 2 * Math.PI * rotateDelta.x / element.clientHeight ); // yes, height

				rotateUp( 2 * Math.PI * rotateDelta.y / element.clientHeight );
				rotateStart.copy( rotateEnd );

			}

			function handleTouchMovePan( event ) {

				if ( event.touches.length == 1 ) {

					panEnd.set( event.touches[ 0 ].pageX, event.touches[ 0 ].pageY );

				} else {

					const x = 0.5 * ( event.touches[ 0 ].pageX + event.touches[ 1 ].pageX );
					const y = 0.5 * ( event.touches[ 0 ].pageY + event.touches[ 1 ].pageY );
					panEnd.set( x, y );

				}

				panDelta.subVectors( panEnd, panStart ).multiplyScalar( scope.panSpeed );
				pan( panDelta.x, panDelta.y );
				panStart.copy( panEnd );

			}

			function handleTouchMoveDolly( event ) {

				const dx = event.touches[ 0 ].pageX - event.touches[ 1 ].pageX;
				const dy = event.touches[ 0 ].pageY - event.touches[ 1 ].pageY;
				const distance = Math.sqrt( dx * dx + dy * dy );
				dollyEnd.set( 0, distance );
				dollyDelta.set( 0, Math.pow( dollyEnd.y / dollyStart.y, scope.zoomSpeed ) );
				dollyOut( dollyDelta.y );
				dollyStart.copy( dollyEnd );

			}

			function handleTouchMoveDollyPan( event ) {

				if ( scope.enableZoom ) handleTouchMoveDolly( event );
				if ( scope.enablePan ) handleTouchMovePan( event );

			}

			function handleTouchMoveDollyRotate( event ) {

	BBZYˆ
ØÛÜK™[˜X›V›ÛÛH
H[™UÝXÚ[Ý™QÛJ]™[
NÂ‚BBBZYˆ
ØÛÜK™[˜X›T›Ý]H
H[™UÝXÚ[Ý™T›Ý]J]™[
NÂ‚‚BB_B‚‚BBY[˜Ý[Ûˆ[™UÝXÚ[™

HÈËÈ›Ë[Ü‚BB_HËÂ‚BBKËÈ]™[[™\œÈH”ÓNˆ\Ý[ˆ›Üˆ]™[È[™™\Ù]Ý]B‚BBKËÂ‚‚‚BBY[˜Ý[ÛˆÛ•Ú[™ÝÔ™\Ú^™J
HÂ‚BBB\ØÛÜK\]J
NÂ‚BB_B‚‚BBY[˜Ý[ÛˆÛÛÛ^Y[J]™[
HÂ‚‚BBBZYˆ
ØÛÜK™[˜X›YOOH˜[ÙH
H™]\›ŽÂ‚BBBY]™[œ™]™[Y˜][

NÂ‚‚BB_B‚‚BBY[˜Ý[ÛˆÛ”Ú[\‘ÝÛŠ]™[
HÂ‚‚BBBZYˆ
ØÛÜK™[˜X›YOOH˜[ÙH
H™]\›ŽÂ‚‚BBB\ÝÚ]Ú
]™[œÚ[\•\H
HÂ‚‚BBBBXØ\ÙH	Û[Ý\ÙIÎ‚‚BBBBXØ\ÙH	Ü[‰Î‚‚BBBBB[Û“[Ý\ÙQÝÛŠ]™[
NÂ‚BBBBBXœ™XZÎÂ‚‚BBBBKËÈÑÈÝXÚ‚BBB_B‚‚BB_B‚‚BBY[˜Ý[ÛˆÛ”Ú[\“[Ý™J]™[
HÂ‚‚BBBZYˆ
ØÛÜK™[˜X›YOOH˜[ÙH
H™]\›ŽÂ‚‚BBB\ÝÚ]Ú
]™[œÚ[\•\H
HÂ‚‚BBBBXØ\ÙH	Û[Ý\ÙIÎ‚‚BBBBXØ\ÙH	Ü[‰Î‚‚BBBBB[Û“[Ý\ÙS[Ý™J]™[
NÂ‚BBBBBXœ™XZÎÂ‚‚BBBBKËÈÑÈÝXÚ‚BBB_B‚‚BB_B‚‚BBY[˜Ý[ÛˆÛ”Ú[\•\
]™[
HÂ‚‚BBB\ÝÚ]Ú
]™[œÚ[\•\H
HÂ‚‚BBBBXØ\ÙH	Û[Ý\ÙIÎ‚‚BBBBXØ\ÙH	Ü[‰Î‚‚BBBBB[Û“[Ý\ÙU\
]™[
NÂ‚BBBBBXœ™XZÎÂ‚‚BBBBKËÈÑÈÝXÚ‚BBB_B‚‚BB_B‚‚BBY[˜Ý[ÛˆÛ“[Ý\ÙQÝÛŠ]™[
HÂ‚‚BBBKËÈ™]™[Hœ›ÝÜÙ\ˆœ›ÛHØÜ›Û[™Ë‚‚BBBY]™[œ™]™[Y˜][

NÂ‚BBB\ØÛÜK™ÛQ[[Y[™›ØÝ\ÈÈØÛÜK™ÛQ[[Y[™›ØÝ\Ê
HˆÚ[™ÝË™›ØÝ\Ê
NÂ‚BBB[][Ý\ÙPXÝ[ÛŽÂ‚‚BBB\ÝÚ]Ú
]™[˜]Ûˆ
HÂ‚‚BBBBXØ\ÙH‚‚BBBBB[[Ý\ÙPXÝ[ÛˆHØÛÜK›[Ý\ÙP]ÛœË“Q•Â‚BBBBBXœ™XZÎÂ‚‚BBBBXØ\ÙHN‚‚BBBBB[[Ý\ÙPXÝ[ÛˆHØÛÜK›[Ý\ÙP]ÛœË“RQNÂ‚BBBBBXœ™XZÎÂ‚‚BBBBXØ\ÙHŽ‚‚BBBBB[[Ý\ÙPXÝ[ÛˆHØÛÜK›[Ý\ÙP]ÛœË”’QÒÂ‚BBBBBXœ™XZÎÂ‚‚BBBYY˜][‚‚BBBBB[[Ý\ÙPXÝ[ÛˆHHNÂ‚‚BBB_B‚‚BBB\ÝÚ]Ú
[Ý\ÙPXÝ[Ûˆ
HÂ‚‚BBBBXØ\ÙH‘QK“SÕTÑK‘ÓN‚‚BBBBBZYˆ
ØÛÜK™[˜X›V›ÛÛHOOH˜[ÙH
H™]\›ŽÂ‚BBBBBZ[™S[Ý\ÙQÝÛ‘ÛJ]™[
NÂ‚BBBBB\Ý]HHÕUK‘ÓNÂ‚BBBBBXœ™XZÎÂ‚‚BBBBXØ\ÙH‘QK“SÕTÑK”“ÕUN‚‚BBBBBZYˆ
]™[˜Ý›Ù^H]™[›Y]RÙ^H]™[œÚYÙ^H
HÂ‚BBBBBBZYˆ
ØÛÜK™[˜X›T[ˆOOH˜[ÙH
H™]\›ŽÂ‚BBBBBBZ[™S[Ý\ÙQÝÛ”[Š]™[
NÂ‚BBBBBB\Ý]HHÕUK”SŽÂ‚BBBBB_H[ÙHÂ‚BBBBBBZYˆ
ØÛÜK™[˜X›T›Ý]HOOH˜[ÙH
H™]\›ŽÂ‚BBBBBBZ[™S[Ý\ÙQÝÛ”›Ý]J]™[
NÂ‚BBBBBB\Ý]HHÕUK”“ÕUNÂ‚BBBBB_B‚BBBBBXœ™XZÎÂ‚‚BBBBXØ\ÙH‘QK“SÕTÑK”SŽ‚‚BBBBBZYˆ
]™[˜Ý›Ù^H]™[›Y]RÙ^H]™[œÚYÙ^H
HÂ‚BBBBBBZYˆ
ØÛÜK™[˜X›T›Ý]HOOH˜[ÙH
H™]\›ŽÂ‚BBBBBBZ[™S[Ý\ÙQÝÛ”›Ý]J]™[
NÂ‚BBBBBB\Ý]HHÕUK”“ÕUNÂ‚BBBBB_H[ÙHÂ‚BBBBBBZYˆ
ØÛÜK™[˜X›T[ˆOOH˜[ÙH
H™]\›ŽÂ‚BBBBBBZ[™S[Ý\ÙQÝÛ”[Š]™[
NÂ‚BBBBBB\Ý]HHÕUK”SŽÂ‚BBBBB_B‚BBBBBXœ™XZÎÂ‚‚BBBYY˜][‚‚BBBBB\Ý]HHÕUK““Ó‘NÂ‚BBB_B‚‚BBBZYˆ
Ý]HOOHÕUK““Ó‘H
HÂ‚BBBB\ØÛÜK™ÛQ[[Y[›ÝÛ™\‘ØÝ[Y[˜Y]™[\Ý[™\Š	ÜÚ[\›[Ý™IËÛ”Ú[\“[Ý™H
NÂ‚BBBB\ØÛÜK™ÛQ[[Y[›ÝÛ™\‘ØÝ[Y[˜Y]™[\Ý[™\Š	ÜÚ[\\	ËÛ”Ú[\•\
NÂ‚BBBB\ØÛÜK™\Ü]Ú]™[
ÜÝ\]™[
NÂ‚BBB_B‚‚BB_B‚‚BBY[˜Ý[ÛˆÛ“[Ý\ÙS[Ý™J]™[
HÂ‚‚BBBZYˆ
ØÛÜK™[˜X›YOOH˜[ÙH
H™]\›ŽÂ‚BBBY]™[œ™]™[Y˜][

NÂ‚‚BBB\ÝÚ]Ú
Ý]H
HÂ‚BBBBXØ\ÙHÕUK”“ÕUN‚‚BBBBBZYˆ
ØÛÜK™[˜X›T›Ý]HOOH˜[ÙH
H™]\›ŽÂ‚BBBBBZ[™S[Ý\ÙS[Ý™T›Ý]J]™[
NÂ‚BBBBBXœ™XZÎÂ‚BBBBXØ\ÙHÕUK‘ÓN‚‚BBBBBZYˆ
ØÛÜK™[˜X›V›ÛÛHOOH˜[ÙH
H™]\›ŽÂ‚BBBBBZ[™S[Ý\ÙS[Ý™QÛJ]™[
NÂ‚BBBBBXœ™XZÎÂ‚BBBBXØ\ÙHÕUK”SŽ‚‚BBBBBZYˆ
ØÛÜK™[˜X›T[ˆOOH˜[ÙH
H™]\›ŽÂ‚BBBBBZ[™S[Ý\ÙS[Ý™T[Š]™[
NÂ‚BBBBBXœ™XZÎÂ‚BBB_B‚‚BB_B‚‚BBY[˜Ý[ÛˆÛ“[Ý\ÙU\

HÂ‚‚BBB\ØÛÜK™ÛQ[[Y[›ÝÛ™\‘ØÝ[Y[œ™[[Ý™Q]™[\Ý[™\Š	ÜÚ[\›[Ý™IËÛ”Ú[\“[Ý™H
NÂ‚BBB\ØÛÜK™ÛQ[[Y[›ÝÛ™\‘ØÝ[Y[œ™[[Ý™Q]™[\Ý[™\Š	ÜÚ[\\	ËÛ•Ú[™ÝÔ™\Ú^™H
NÂ‚BBBZYˆ
ØÛÜK™[˜X›YOOH˜[ÙH
H™]\›ŽÂ‚BBB\ØÛÜK™\Ü]Ú]™[
Ù[™]™[
NÂ‚BBB\Ý]HHÕUK““Ó‘NÂ‚BB_B‚‚BB\ØÛÜK™ÛQ[[Y[˜Y]™[\Ý[™\Š	ØÛÛ^Y[IËÛÛÛ^Y[H
NÂ‚BB\ØÛÜK™ÛQ[[Y[˜Y]™[\Ý[™\Š	ÜÚ[\™ÝÛ‰ËÛ”Ú[\‘ÝÛˆ
NÂ‚BB\ØÛÜK™ÛQ[[Y[˜Y]™[\Ý[™\Š	ÝÚY[	ËÛ“[Ý\ÙUÚY[È\ÜÚ]™Nˆ˜[ÙHH
NÂ‚BB\ØÛÜK™ÛQ[[Y[˜Y]™[\Ý[™\Š	ÝÝXÚÝ\	ËÛ•ÝXÚÝ\È\ÜÚ]™Nˆ˜[ÙHH
NÂ‚BB\ØÛÜK™ÛQ[[Y[˜Y]™[\Ý[™\Š	ÝÝXÚ[™	ËÛ•ÝXÚ[™
NÂ‚BB\ØÛÜK™ÛQ[[Y[˜Y]™[\Ý[™\Š	ÝÝXÚ[Ý™IËÛ•Ú[™ÝÔ™\Ú^™KÈ\ÜÚ]™Nˆ˜[ÙHH
NÂ‚‚BB]\Ë\]J
NÂ‚B_B‚_B‚‚U‘QK“X\ÛÛ›ÛÈHX\ÛÛ›ÛÎÂ‚U‘QK“Ü˜š]ÛÛ›ÛÈHÜ˜š]ÛÛ›ÛÎÂŸH
J
NÂ