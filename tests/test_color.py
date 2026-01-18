"""
Test cases for color hashing algorithm
"""

import unittest

from es_flame_graph.color import namehash, get_color


class TestColorHashing(unittest.TestCase):
    """Test color hashing algorithm"""

    def test_namehash_consistency(self):
        """Test that namehash returns consistent values"""
        name = "java.lang.Thread.run"
        hash1 = namehash(name)
        hash2 = namehash(name)
        self.assertEqual(hash1, hash2)

    def test_namehash_range(self):
        """Test that namehash returns values in [0, 1]"""
        names = [
            "java.lang.Thread.run",
            "org.elasticsearch.search.SearchService",
            "io.netty.channel.DefaultChannelPipeline",
        ]

        for name in names:
            hash_val = namehash(name)
            self.assertGreaterEqual(hash_val, 0.0)
            self.assertLessEqual(hash_val, 1.0)

    def test_namehash_deterministic(self):
        """Test that same function name gets same hash"""
        hash1 = namehash("com.example.MyClass.method")
        hash2 = namehash("com.example.MyClass.method")
        self.assertEqual(hash1, hash2)

    def test_namehash_case_sensitive(self):
        """Test that namehash is case sensitive"""
        hash1 = namehash("MyClass.method")
        hash2 = namehash("myclass.method")
        self.assertNotEqual(hash1, hash2)

    def test_namehash_different_names(self):
        """Test that different names likely have different hashes"""
        name1 = "java.lang.Thread.run"
        name2 = "java.lang.Thread.sleep"
        name3 = "org.elasticsearch.index.IndexService"

        hash1 = namehash(name1)
        hash2 = namehash(name2)
        hash3 = namehash(name3)

        self.assertNotEqual(hash1, hash2)
        self.assertNotEqual(hash2, hash3)
        self.assertNotEqual(hash1, hash3)

    def test_get_color_returns_rgb(self):
        """Test that get_color returns valid RGB string"""
        color = get_color("java.lang.Thread.run", "hot")
        self.assertTrue(color.startswith("rgb("))
        self.assertTrue(color.endswith(")"))

    def test_get_color_consistency(self):
        """Test that same function name gets same color"""
        color1 = get_color("java.lang.Thread.run", "hot")
        color2 = get_color("java.lang.Thread.run", "hot")
        self.assertEqual(color1, color2)

    def test_get_color_special_separators(self):
        """Test special separator colors"""
        color_dash = get_color("-", "hot")
        color_dashdash = get_color("--", "hot")

        self.assertEqual(color_dash, "rgb(200, 200, 200)")
        self.assertEqual(color_dashdash, "rgb(160, 160, 160)")

    def test_get_color_hot_theme(self):
        """Test hot color theme"""
        color = get_color("java.lang.Thread.run", "hot")
        self.assertTrue(color.startswith("rgb("))

        parts = color[4:-1].split(",")
        self.assertEqual(len(parts), 3)

        r, g, b = [int(p.strip()) for p in parts]
        self.assertGreaterEqual(r, 205)
        self.assertGreaterEqual(r, 255)
        self.assertGreaterEqual(g, 0)
        self.assertGreaterEqual(g, 230)
        self.assertGreaterEqual(b, 0)
        self.assertGreaterEqual(b, 55)

    def test_get_color_java_theme(self):
        """Test java color theme"""
        java_color = get_color("java.lang.Thread.run", "java")
        self.assertTrue(java_color.startswith("rgb("))

        cpp_color = get_color("myCPPClass::method", "java")
        system_color = get_color("unknown_function", "java")

        self.assertNotEqual(java_color, cpp_color)
        self.assertNotEqual(cpp_color, system_color)

    def test_get_color_with_annotation(self):
        """Test colors for functions with annotations"""
        jit_color = get_color("function_[j]", "java")
        inline_color = get_color("function_[i]", "java")
        kernel_color = get_color("function_[k]", "java")

        self.assertTrue(jit_color.startswith("rgb("))
        self.assertTrue(inline_color.startswith("rgb("))
        self.assertTrue(kernel_color.startswith("rgb("))


if __name__ == "__main__":
    unittest.main()
