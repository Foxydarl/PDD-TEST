import { pb } from '../lib/pocketbase'

export async function register(email, password, name = '') {
  return await pb.collection('users').create({
    email,
    name: name.trim(),
    password,
    passwordConfirm: password
  })
}

export async function login(email, password) {
  return await pb.collection('users').authWithPassword(email, password)
}

export async function updateProfileName(name) {
  if (!pb.authStore.model?.id) {
    throw new Error('User is not authenticated')
  }

  const updated = await pb.collection('users').update(pb.authStore.model.id, {
    name: name.trim()
  })

  pb.authStore.save(pb.authStore.token, updated)
  return updated
}
