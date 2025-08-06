# Import step modules
from backend.steps.git import GitClone, GitCloneResult
from backend.steps.checkout_merged import CheckoutMergedResult
from backend.steps.checkout_merged import CheckoutMerged
from steps.gradle_build import GradleBuild, GradleBuildResult

# Process releases flow
def process_release(release_id):
    if release_id not in releases:
        return
    
    release = releases[release_id]
    if release.state != 'Active':
        return
    
    try:
        # Step 1: Git Clone
        git_clone = GitClone()
        clone_result = git_clone.process(release.git_url)
        
        with state_lock:
            release.clone = clone_result
            socketio.emit('release_updated', asdict(release))
        
        if not clone_result.success:
            logger.error(f"Git clone failed for release {release_id}: {clone_result.error_message}")
            return
        
        # Step 2: Checkout Merged
        checkout_merged = CheckoutMerged()
        checkout_result = checkout_merged.process(clone_result, release.branches)
        
        with state_lock:
            release.checkout_merged = checkout_result
            socketio.emit('release_updated', asdict(release))
        
        if not checkout_result.success:
            logger.error(f"Checkout merged failed for release {release_id}: {checkout_result.error_message}")
            return
        
        # Step 3: Gradle Build
        gradle_build = GradleBuild()
        build_result = gradle_build.process(checkout_result, "jib")
        
        with state_lock:
            release.gradle_build = build_result
            socketio.emit('release_updated', asdict(release))
        
        if not build_result.success:
            logger.error(f"Gradle build failed for release {release_id}: {build_result.error_message}")
            return
        
    except Exception as e:
        error_msg = f"Error processing release {release_id}: {str(e)}"
        logger.error(error_msg)
        socketio.emit('error', {'message': error_msg})

@app.route('/api/releases', methods=['GET'])
def get_releases():
    return jsonify([asdict(r) for r in releases.values()])

@app.route('/api/releases', methods=['POST'])
def create_release():
    data = request.json
    branches_to_merge = data.get('branches', [])
    state = data.get('state', 'Pause')
    
    if not branches_to_merge:
        return jsonify({'error': 'No branches selected'}), 400
    
    release_id = hashlib.md5(''.join(sorted(branches_to_merge)).encode()).hexdigest()
    
    if release_id in releases:
        return jsonify({'error': 'Release with these branches already exists'}), 409
    
    release = ReleaseDto(
        id=release_id,
        branches=branches_to_merge,
        state=state,
        git_url=GIT_REPO_URL
    )
    
    with state_lock:
        releases[release_id] = release
    
    socketio.emit('release_created', asdict(release))
    
    if state == 'Active':
        thread = threading.Thread(target=process_release, args=(release_id,))
        thread.daemon = True
        thread.start()
    
    return jsonify(asdict(release)), 201

@app.route('/api/releases/<release_id>', methods=['PUT'])
def update_release(release_id):
    if release_id not in releases:
        return jsonify({'error': 'Release not found'}), 404
    
    data = request.json
    release = releases[release_id]
    old_state = release.state
    new_state = data.get('state', old_state)
    
    if old_state != new_state:
        release.state = new_state
        
        with state_lock:
            releases[release_id] = release
        
        socketio.emit('release_updated', asdict(release))
        
        if old_state == 'Pause' and new_state == 'Active':
            thread = threading.Thread(target=process_release, args=(release_id,))
            thread.daemon = True
            thread.start()
    
    return jsonify(asdict(release))

@app.route('/api/releases/<release_id>', methods=['DELETE'])
def delete_release(release_id):
    if release_id not in releases:
        return jsonify({'error': 'Release not found'}), 404
    
    with state_lock:
        release = releases.pop(release_id)
    
    socketio.emit('release_deleted', {'id': release_id})
    
    return jsonify({'success': True})
