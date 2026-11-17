'use strict';

// Private essays must never enter public posts, archives, tags or generated pages.
hexo.extend.filter.register('before_generate', function () {
  const posts = hexo.locals.get('posts').toArray();
  const pages = hexo.locals.get('pages').toArray();
  const isPrivateEssay = item =>
    item.layout === 'essay' || item.layout === 'essays' ||
    /^essays(?:\/|$)/.test(item.path || '') ||
    (item.categories && item.categories.toArray().some(category => category.name === '随笔'));
  if (posts.concat(pages).some(isPrivateEssay)) {
    throw new Error('随笔为私人内容，请存入根目录“私人随笔”，不能放在公开 source 中。');
  }
});
