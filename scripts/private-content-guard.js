'use strict';

// Public essays are allowed, but the private article must never enter the build.
hexo.extend.filter.register('before_generate', function () {
  const posts = hexo.model('Post').toArray();
  const pages = hexo.model('Page').toArray();
  const isPrivateEssay = item =>
    item.private === true || item.title === '关键节点' ||
    /(?:^|[\\/])essay-2026-09-12\.md$/.test(item.source || '') ||
    /^essays\/2026-09-12(?:\/|$)/.test(item.path || '') ||
    /^essays\/2026-09-12(?:\/|$)/.test(item.permalink || '');
  if (posts.concat(pages).some(isPrivateEssay)) {
    throw new Error('《关键节点》及标记 private 的文章为私人内容，只能存入根目录“私人随笔”。');
  }
});
